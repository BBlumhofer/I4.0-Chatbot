from __future__ import annotations

import asyncio
import time
from typing import Type, TypeVar

import asyncua
import structlog
from asyncua import Node, ua
from asyncua.crypto.cert_gen import generate_private_key, generate_self_signed_app_certificate

from pyuaadapter.common import setup_logging
from pyuaadapter.server.base_config import BaseConfig
from pyuaadapter.server.base_module import BaseModule
from pyuaadapter.server.ua_types import UaTypes

M = TypeVar("M", bound="BaseModule")

# TODO add support for password-protected private keys

def _create_key_and_certificate(config: BaseConfig) -> None:
    from cryptography import x509
    from cryptography.hazmat._oid import ExtendedKeyUsageOID
    from cryptography.hazmat.primitives import serialization

    # Generate new key
    key = generate_private_key()
    with open(config.ENCRYPTION_PRIVATE_KEY, "wb") as f:
        f.write(key.private_bytes(encoding=serialization.Encoding.PEM,
                                  format=serialization.PrivateFormat.TraditionalOpenSSL,
                                  encryption_algorithm=serialization.NoEncryption()))

    # Generate new self-signed certificate based on that key
    cert = generate_self_signed_app_certificate(
        private_key=key, common_name=config.SERVER_NAME, names={},
        subject_alt_names=[
            x509.UniformResourceIdentifier("urn:freeopcua:python:server")  # TODO config, must be equal to OPC UA app URI !
        ],
        extended=[ExtendedKeyUsageOID.SERVER_AUTH, ExtendedKeyUsageOID.CLIENT_AUTH],
        days=3650
    )

    with open(config.ENCRYPTION_CERTIFICATE_PATH, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.DER))


class Server:
    ns_idx: int
    _ua_machines: Node

    def __init__(self, config: BaseConfig):
        self.config = config
        self._ua_server = asyncua.Server()
        self._modules: list[BaseModule] = []
        self.running = False

        setup_logging(log_levels=config.LOG_LEVELS, log_format=config.LOG_FORMAT)
        self.logger = structlog.stdlib.get_logger("sf.server.Server")

    async def init(self) -> None:
        await self._setup_ua_server()

        self.ns_idx = await UaTypes.init_class(self._ua_server, self.config)
        self._ua_machines = await self._ua_server.nodes.objects.get_child(f"{UaTypes.ns_machinery}:Machines")

        if self.config.MODULE is not None:  # TODO remove when no longer required for backwards compatibility
            await self.add_module(self.config.MODULE)  # type: ignore

    async def _setup_ua_server(self) -> None:
        # Configure server to use sqlite as history database (default is a simple memory dict)
        if self.config.HISTORY == "SQLite":
            from asyncua.server.history_sql import HistorySQLite
            self._ua_server.iserver.history_manager.set_storage(HistorySQLite("opcua_history.sql"))

        if self.config.ENCRYPTION:
            self.logger.info("Encryption enabled!")
            try:
                await self._ua_server.load_certificate(self.config.ENCRYPTION_CERTIFICATE_PATH)
                await self._ua_server.load_private_key(self.config.ENCRYPTION_PRIVATE_KEY)
                self.logger.info("Loaded existing encryption key and certificate!")
            except FileNotFoundError:
                self.logger.info("Creating new encryption key and certificate...")
                _create_key_and_certificate(self.config)

                await self._ua_server.load_certificate(self.config.ENCRYPTION_CERTIFICATE_PATH)
                await self._ua_server.load_private_key(self.config.ENCRYPTION_PRIVATE_KEY)

        await self._ua_server.init()

        if self.config.DEBUG:
            self.logger.warning("DEBUG mode enabled!")

        self._ua_server.set_endpoint(self.config.ENDPOINT_ADDRESS)
        self._ua_server.set_server_name(self.config.SERVER_NAME)

        # TODO? SecurityPolicy "None" shall be disabled when Encryption is available according to OPC UA spec
        #  https://profiles.opcfoundation.org/profile/762
        if not self.config.ENCRYPTION:
            self._ua_server.set_security_policy([ua.SecurityPolicyType.NoSecurity])
        self._ua_server.set_identity_tokens([ua.UserNameIdentityToken])

    async def add_module(self, module: M | Type[M], **kwargs) -> M:
        time_start = time.monotonic()
        if isinstance(module, type(BaseModule)):  # given a class, instantiate etc. ourselves
            self.logger.debug("Instantiating new module instance...", module=module, kwargs=kwargs)
            module = module(**kwargs, server=self._ua_server, ns_idx=self.ns_idx, config=self.config)
            await module.init(self._ua_machines)

        self._modules.append(module)  # type: ignore
        self.logger.info("Added module", module_name=module.full_name, elapsed=time.monotonic()-time_start)

        return module  # type: ignore

    @property
    def modules(self) -> list[BaseModule]:
        return self._modules

    @property
    def machines(self) -> list[BaseModule]:
        return self._modules

    @property
    def ua_server(self) -> asyncua.Server:
        return self._ua_server

    async def _register_server(self, retry_seconds: float = 10.0):
        lds_client = asyncua.Client(self.config.DISCOVERY_SERVER_ADDRESS)
        while self.running:
            try:
                await lds_client.register_server(self._ua_server)
            except Exception:
                try:
                    await lds_client.connect()
                except Exception:
                    self.logger.error(f"Failed to register to discovery server, retrying in {retry_seconds} seconds.",
                                      discovery_server_address=self.config.DISCOVERY_SERVER_ADDRESS)
            await asyncio.sleep(retry_seconds)

    async def start(self, blocking: bool = True) -> None:
        """ Starts the OPC UA server and blocks until server shutdown if blocking == True. """
        await self._ua_server.start()
        for endpoint in await self._ua_server.get_endpoints():
            self.logger.info("Serving OPC UA server at:", endpoint_url=endpoint.EndpointUrl,
                             security_policy_uri=endpoint.SecurityPolicyUri)
        self.running = True

        if self.config.REGISTER_AT_DISCOVERY_SERVER:
            asyncio.create_task(self._register_server(), name="DiscoveryRegisterTask")
        else:
            self.logger.warning("Register at Discovery server is disabled!")

        if blocking:
            # monitor how busy the event loop is and warn if it is probably too busy
            sleep_time = 1
            while self.running:
                before = time.time()
                await asyncio.sleep(sleep_time)
                delta = time.time() - before
                if delta > 1.5 * sleep_time:
                    self.logger.warning("Event loop is too busy!", delta=delta, sleep_time=sleep_time)

    async def shutdown(self) -> None:
        self.running = False

        for module in self.modules:
            self.logger.debug("Trying to call shutdown()...", module_name=module.name)
            try:
                await module.shutdown()
            except Exception as ex:  # shutdown() is implemented by user, might raise some exception
                self.logger.exception(ex)
