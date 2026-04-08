import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL = process.env.API_URL ?? "http://api:8000";

async function proxyRequest(
  req: NextRequest,
  params: { _path: string[] },
): Promise<NextResponse> {
  const path = params._path.join("/");
  const url = new URL(`${API_BASE_URL}/${path}`);
  const incomingUrl = new URL(req.url);
  incomingUrl.searchParams.forEach((value, key) => {
    url.searchParams.append(key, value);
  });

  const headers = new Headers(req.headers);
  headers.delete("host");
  headers.delete("connection");

  const method = req.method.toUpperCase();
  const hasBody = method !== "GET" && method !== "HEAD";

  const upstream = await fetch(url, {
    method,
    headers,
    body: hasBody ? await req.text() : undefined,
    cache: "no-store",
  });

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: upstream.headers,
  });
}

type RouteContext = {
  params: Promise<{ _path: string[] }>;
};

export async function GET(req: NextRequest, context: RouteContext) {
  return proxyRequest(req, await context.params);
}

export async function POST(req: NextRequest, context: RouteContext) {
  return proxyRequest(req, await context.params);
}

export async function PUT(req: NextRequest, context: RouteContext) {
  return proxyRequest(req, await context.params);
}

export async function PATCH(req: NextRequest, context: RouteContext) {
  return proxyRequest(req, await context.params);
}

export async function DELETE(req: NextRequest, context: RouteContext) {
  return proxyRequest(req, await context.params);
}

export const runtime = "nodejs";
