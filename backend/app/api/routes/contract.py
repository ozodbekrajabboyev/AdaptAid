"""Routes used only by the frontend proxy contract test (ENABLE_CONTRACT_ROUTES=true).

They exercise the cases a naive reverse proxy gets wrong: several Set-Cookie headers,
gzip bodies, 204 responses, error statuses, multipart uploads, file downloads,
query strings and redirects.
"""

from fastapi import APIRouter, File, Form, Request, Response, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse

router = APIRouter(prefix="/_contract", tags=["contract"])


@router.get("/cookies")
def cookies() -> Response:
    resp = JSONResponse({"set": ["a", "b"]})
    resp.set_cookie("contract_a", "1", httponly=True, samesite="lax", path="/")
    resp.set_cookie("contract_b", "2", httponly=True, samesite="lax", path="/")
    return resp


@router.get("/echo")
def echo(request: Request) -> dict:
    return {
        "method": request.method,
        "query": dict(request.query_params),
        "cookies": dict(request.cookies),
    }


@router.post("/echo")
async def echo_post(request: Request) -> dict:
    body = await request.json()
    return {"method": request.method, "body": body, "query": dict(request.query_params)}


@router.get("/big")
def big() -> dict:
    # Large enough for GZipMiddleware (minimum_size=1000) to compress it.
    return {"items": [{"i": i, "text": "lorem ipsum dolor sit amet " * 3} for i in range(300)]}


@router.delete("/nothing", status_code=204)
def nothing() -> Response:
    return Response(status_code=204)


@router.get("/error")
def error() -> Response:
    return JSONResponse({"detail": "Teapot says no"}, status_code=418)


@router.post("/upload")
async def upload(file: UploadFile = File(...), note: str = Form(...)) -> dict:
    data = await file.read()
    return {"filename": file.filename, "size": len(data), "note": note}


@router.get("/csv")
def csv() -> Response:
    return PlainTextResponse(
        "a,b\n1,2\n",
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="contract.csv"'},
    )


@router.get("/redirect")
def redirect(request: Request) -> Response:
    # Absolute URL pointing at the backend's own origin: the proxy must not leak it.
    return RedirectResponse(str(request.url_for("echo")) + "?from=redirect", status_code=307)
