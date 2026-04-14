# CA-Module_Architecture

## Seite 1

Module_ArchitectureModul-ArchitekturSystem OverviewThe CA-Modul (Collaborative Assembly Module) is a sophisticated manufacturing system that integrates multiple components for automatedand collaborative assembly operations. The system features comprehensive access control, real-time monitoring, and flexible skill-basedexecution.
Key System Features
Components
Monitoring
ParameterSet
SkillsAssembleSkill
Expected Behavior:
ParameterSet
Monitoring
FinalResultData
StoreSkill
Expected Behavior:
Access Control: Role-based permissions with AAS integration (Details)Collaborative Operation: Human-robot interaction with safety protocolsModular Architecture: Component-based design for flexibility and maintainabilityReal-time Communication: MQTT-based event publishing and monitoring
RobotWorker StationSafetyStoragePortsCompressorCompressor
?
?
Assembles a product based Steps assigned to this module from the production plan.The skill will throw an MissingArgumentException if the GoalProductID or the InitialProductsList is not specified.The skill will throw an InvalidArgumentException if the GoalProductID is not a valid ProductID.The skill will throw an InvalidArgumentException if the InitialProductsList contains invalid ProductIDs (not existing or not the correct type).The skill checks if there is a valid worker assigned to the module and will go in halted if the task cannot be done by the worker.The skill checks if all products required for the assembly are available and will go in halted if the task cannot be done due to missingproducts.
GoalProductID (String)InitialProducts (List(String))?
ExecutedAssemblySteps (Int)CurrentAssemblyStep (Int)RemainingAssemblySteps (Int)ElapsedTime (Real)
SuccessfullyExecutedAssemblySteps (Int)ElapsedTime (Real)SuccessfulExecutionsCount (Int)
Stores a product from port in a storage component assigned to this module.If no PlaceSlotId is specified, the skill will store the product in the first available slot.If a PlaceSlotId is specified, the skill will store the product in the specified slot.


# CA-Module_Architecture

## Seite 2

ParameterSet
Monitoring
FinalResultData
RetrieveSkill
Expected Behavior:
ParameterSet
Monitoring
FinalResultData
SolderSemitrailerSkill
Expected Behavior:
If a PlaceSlotId is written in PlaceSlotID but SpecifySlot is set to false, the skill will store the product in the first available slot.If the PlaceSlotId is specified but the slot is already occupied, the skill raises an InvalidArgument Exception.If the PlaceSlotId is specified but the slot does not exist, the skill raises an InvalidArgument Exception.If the PickPort is not specified, the skill raises an MissingArgument Exception.If the PickPort is specified but the port is not coupled, the skill raises an InvalidArgument Exception.
ProductID (String)SpecifySlot (Bool)PlaceSlotId (Int)PickPort (Int)
ElapsedTime (Real)GoalSlot (Int)
SuccessfulExecutionsCount (Int)ElapsedTime (Real)PlacedSlot (Int)
Retrieves a product from a storage component assigned to this module.If the ProductID is specified, the skill will retrieve the product with the specified ProductID.If the WorkpieceCarrierID is specified, the skill will retrieve the product with the specified WorkpieceCarrierID.If the ProductType is specified, the skill will retrieve the first product with the specified ProductType.It can only be specified one of the three parameters (ProductID, WorkpieceCarrierID, ProductType).If the PickPort is not specified, the skill raises an MissingArgument Exception.If the PickPort is specified but the port is not coupled, the skill raises an InvalidArgument Exception.If the specified product is not available in the storage, the skill raises an InvalidArgument Exception.
ProductID (String)ProductType (String)WorkpieceCarrierID (String)DepleteByProductID (Bool)DepleteByProductType (Bool)DepleteByWorkpieceCarrierID (Bool)PlacePort (Int)
ElapsedTime (Real)PickSlot (Int)
SuccessfulExecutionsCount (Int)ElapsedTime (Real)
During the Execution the Robot picks the part from its storage and places it on the soldering station.The robot changes its tool to the soldering tool.The robot solders the part.The robot changes its tool back to the Gripper.The robot picks the part from the soldering station and places it back in the same storage slot.Solder a Semitrailer with the specified ProductID.If the ProductID is not specified, the skill raises an MissingArgument Exception.If the ProductID is specified but the product is not available, the skill raises an InvalidArgument Exception.If the ProductType is specified but the product is not a Semitrailer, the skill raises an InvalidArgument Exception.If the Slot the product is picked from is not free when the product is placed back, the robot will choose the next free slot.


# CA-Module_Architecture

## Seite 3

ParameterSet
Monitoring
FinalResultData
StartupSkill
Expected Behavior:
Kompressor-Reset-Funktionalität:
Monitoring
ShutdownSkill
HandoverToWorker Skill
Expected Behavior:
ParameterSet
Monitoring
FinalResultData
AssignProductIdSkill
Expected Behavior:
ProductID (String)ProductType (String)
ElapsedTime (Real)
SuccessfulExecutionsCount (Int)ElapsedTime (Real)ConsumedEnergy (Real)
Initialisiert das Modul und führt kontinuierliche Überwachungsaufgaben ausImplementiert automatische Kompressor-Reset-Funktionalität alle 60 MinutenÜberwacht den Anmeldezustand des Workers (bei Worker Station)Steuert Tischbewegungen automatisch basierend auf HöhenänderungenGeht in den RUNNING-Zustand über, nachdem die Startup-Phase abgeschlossen istFührt kontinuierliche Systemwartung und Überwachung durch
Alle 3600 Sekunden (60 Minuten) wird die Kompressor-Reset-Methode automatisch ausgeführtProtokolliert: "Resetting compressor every 60 minutes"Nutzt die ResetCompressor-Methode der Kompressor-Komponente
Uptime (Real)
Hands over a product to a worker from storage.The skill can retrieve by ProductID, ProductType, WorkpieceCarrierID, or SlotID.Only one of the retrieval methods can be specified at a time.If multiple retrieval parameters are specified, the skill raises an InvalidArgument Exception.If no Worker is registered, the skill raises a BadInvalidState Exception.If gesture recognition is active, the robot waits for worker gesture confirmation.The robot places the product in the worker's hand or designated handover position.
ProductID (String)ProductType (String)WorkpieceCarrierID (String)SlotID (Int)HandoverByProductID (Bool)HandoverByProductType (Bool)HandoverByWorkpieceCarrierID (Bool)HandoverBySlotID (Bool)ActivateGestureRecognition (Bool)
ElapsedTime (Real)
SuccessfulExecutionsCount (Int)ElapsedTime (Real)PickSlot (Int)


# CA-Module_Architecture

## Seite 4

ParameterSet
Monitoring
FinalResultData
Assigns a product ID to a product without an ID in storage.The skill searches for a product of the specified ProductType that has no ProductID assigned.If no product of the specified type without ID is found, the skill raises an InvalidArgument Exception.The skill will assign the specified ProductID to the first matching product found.
ProductID (String)ProductType (String)
ElapsedTime (Real)
SuccessfulExecutionsCount (Int)ElapsedTime (Real)
