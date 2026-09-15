import inspect
from collections.abc import Callable

from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse, Response


async def default_response(
    service_callable: Callable,
    *args,
    exclude_data: tuple[str, ...] = (),
    on_success: Callable[[Response, dict], None] | None = None,
    **kwargs,
) -> Response:
    result = service_callable(*args, **kwargs)

    if inspect.isawaitable(result):
        result = await result

    if result["status_code"] == 204:
        response = Response(status_code=204)
    else:
        data = {key: value for key, value in result["data"].items() if key not in exclude_data}
        response = JSONResponse(
            status_code=result["status_code"],
            content=jsonable_encoder({"message": result["message"], "data": data}),
        )

    if result["status"] and on_success:
        on_success(response, result)

    return response
