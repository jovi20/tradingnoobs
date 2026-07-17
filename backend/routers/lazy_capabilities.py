"""Lazy dispatch for deployment-allowlisted optional capability routes."""
from __future__ import annotations

from copy import copy
from importlib import import_module
from typing import Awaitable, Callable

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import Response
from fastapi.routing import APIRoute

from routers.disabled_capabilities import LazyCapabilityRoute


RouteHandler = Callable[[Request], Awaitable[Response]]


def _application_route_handler(
    application: FastAPI,
    *,
    module_name: str,
    router_attribute: str,
    route_name: str,
    method: str,
) -> RouteHandler:
    cache = getattr(application.state, "lazy_capability_route_handlers", None)
    if cache is None:
        cache = {}
        application.state.lazy_capability_route_handlers = cache
    cache_key = (module_name, router_attribute, route_name, method)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    module = import_module(module_name)
    source_router = getattr(module, router_attribute)
    source_route = next(
        (
            route
            for route in source_router.routes
            if isinstance(route, APIRoute)
            and route.name == route_name
            and method in route.methods
        ),
        None,
    )
    if source_route is None:
        raise RuntimeError(
            f"Lazy capability route target not found: {module_name}.{router_attribute}:{route_name}"
        )

    local_route = copy(source_route)
    local_route.dependency_overrides_provider = application
    handler = local_route.get_route_handler()
    cache[cache_key] = handler
    return handler


def build_lazy_capability_router(
    *,
    prefix: str,
    module_name: str,
    router_attribute: str,
    routes: tuple[LazyCapabilityRoute, ...],
) -> APIRouter:
    """Create hidden stubs that import real handlers only after preflight succeeds."""

    router = APIRouter(prefix=prefix, include_in_schema=False)
    prefix_key = prefix.strip("/").replace("/", "_").replace("-", "_") or "root"

    def build_dispatcher(method: str, route_name: str):
        async def dispatch(request: Request):
            handler = _application_route_handler(
                request.app,
                module_name=module_name,
                router_attribute=router_attribute,
                route_name=route_name,
                method=method,
            )
            return await handler(request)

        return dispatch

    for index, (method, path, route_name) in enumerate(routes):
        router.add_api_route(
            path,
            build_dispatcher(method, route_name),
            methods=[method],
            name=f"lazy_{prefix_key}_{index}_{route_name}",
        )
    return router
