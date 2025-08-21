from urllib.parse import urlparse

import aiohttp
import requests
from typing import (
    TYPE_CHECKING,
    Any,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
)

from pydantic import BaseModel
from typing_extensions import Literal, get_args

# from aiagentplatformpy.config import DEFAULT_CONNECTION_LIMITS, DEFAULT_TIMEOUT
from aiagentplatformpy.exception import AiAgentPlatform_PKCE_AUTH_ERROR_TYPE_ENUMS, AiAgentPlatformAPIError, AiAgentPlatformPKCEAuthError, AiAgentPlatformPKCEAuthErrorType
# from aiagentplatformpy.log import log_debug, log_warning
from aiagentplatformpy.model import (
    AsyncIteratorHTTPResponse,
    FileHTTPResponse,
    HTTPRequest,
    IteratorHTTPResponse,
    ListResponse,
)


if TYPE_CHECKING:
    from aiagentplatformpy.auth import Auth

T = TypeVar("T", bound=BaseModel)


class Requester:
    """
    http request helper class.
    """

    def __init__(
        self,
        auth: Optional["Auth"] = None,
        session: Optional[requests.Session] = None,
        a_session: Optional[aiohttp.ClientSession] = None,
    ):
        self._auth = auth
        self._session = session if session else requests.Session()
        self.a_session = a_session

    def make_request(
        self,
        method: str,
        url: str,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        json: Optional[dict] = None,
        files: Optional[dict] = None,
        cast: Union[Type[T], List[Type[T]], Type[ListResponse[T]], Type[FileHTTPResponse], None] = None,
        data_field: str = "data",
        stream: bool = False,
    ) -> HTTPRequest:
        if headers is None:
            headers = {}
        # headers["User-Agent"] = user_agent()
        # headers["X-AiAgentPlatform-Client-User-Agent"] = aiagentplatform_client_user_agent()
        if self._auth.__class__.__name__ == "TokenAuth":
            self._auth.authentication(headers)
        elif self._auth.__class__.__name__ == "AppAkskAuth":
            parsed_url = urlparse(url)
            host = parsed_url.netloc
            uri = parsed_url.path
            self._auth.ak_sk_sign(method, host, uri, headers, json)

        # log_debug(
        #     "request %s#%s sending, params=%s, json=%s, stream=%s",
        #     method,
        #     url,
        #     params,
        #     json,
        #     stream,
        # )

        return HTTPRequest(
            method=method,
            url=url,
            params=params,
            headers=headers,
            json_body=json,
            files=files,
            stream=stream,
            data_field=data_field,
            cast=cast,
        )

    @overload
    def request(
        self,
        method: str,
        url: str,
        stream: Literal[False],
        cast: Type[T],
        params: dict =...,
        headers: Optional[dict] =...,
        body: dict =...,
        files: dict =...,
        data_field: str =...,
    ) -> T:
       ...

    @overload
    def request(
        self,
        method: str,
        url: str,
        stream: Literal[False],
        cast: List[Type[T]],
        params: dict =...,
        headers: Optional[dict] =...,
        body: dict =...,
        files: dict =...,
        data_field: str =...,
    ) -> List[T]:
       ...

    @overload
    def request(
        self,
        method: str,
        url: str,
        stream: Literal[False],
        cast: Type[ListResponse[T]],
        params: dict =...,
        headers: Optional[dict] =...,
        body: dict =...,
        files: dict =...,
        data_field: str =...,
    ) -> ListResponse[T]:
       ...

    @overload
    def request(
        self,
        method: str,
        url: str,
        stream: Literal[False],
        cast: Type[FileHTTPResponse],
        params: dict =...,
        headers: Optional[dict] =...,
        body: dict =...,
        files: dict =...,
        data_field: str =...,
    ) -> FileHTTPResponse:
       ...

    @overload
    def request(
        self,
        method: str,
        url: str,
        stream: Literal[True],
        cast: None,
        params: dict =...,
        headers: Optional[dict] =...,
        body: dict =...,
        files: dict =...,
        data_field: str =...,
    ) -> IteratorHTTPResponse[str]:
       ...

    @overload
    def request(
        self,
        method: str,
        url: str,
        stream: Literal[False],
        cast: None,
        params: dict =...,
        headers: Optional[dict] =...,
        body: dict =...,
        files: dict =...,
        data_field: str =...,
    ) -> None:
       ...

    def request(
        self,
        method: str,
        url: str,
        stream: Literal[True, False],
        cast: Union[Type[T], List[Type[T]], Type[ListResponse[T]], Type[FileHTTPResponse], None],
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        body: Optional[dict] = None,
        files: Optional[dict] = None,
        data_field: str = "data",
    ) -> Union[T, List[T], ListResponse[T], IteratorHTTPResponse[str], FileHTTPResponse, None]:
        """
        Send a request to the server.
        """
        method = method.upper()

        request = self.make_request(
            method,
            url,
            params=params,
            headers=headers,
            json=body,
            files=files,
            cast=cast,
            data_field=data_field,
            stream=stream,
        )

        return self.send(request)

    def send(
        self,
        request: HTTPRequest,
    ) -> Union[T, List[T], ListResponse[T], IteratorHTTPResponse[str], FileHTTPResponse, None]:
        """
        Send a request to the server.
        """
        return self._parse_response(
            method=request.method,
            url=request.url,
            stream=request.stream,
            response=self._session.request(
                request.method,
                request.url,
                params=request.params,
                headers=request.headers,
                json=request.json_body,
                files=request.files,
                stream=request.stream,
            ),
            cast=request.cast,
            data_field=request.data_field,
        )

    @overload
    async def arequest(
        self,
        method: str,
        url: str,
        stream: Literal[False],
        cast: Type[T],
        params: dict =...,
        headers: Optional[dict] =...,
        body: dict =...,
        files: dict =...,
        data_field: str =...,
    ) -> T:
       ...

    @overload
    async def arequest(
        self,
        method: str,
        url: str,
        stream: Literal[False],
        cast: List[Type[T]],
        params: dict =...,
        headers: Optional[dict] =...,
        body: dict =...,
        files: dict =...,
        data_field: str =...,
    ) -> List[T]:
       ...

    @overload
    async def arequest(
        self,
        method: str,
        url: str,
        stream: Literal[False],
        cast: Type[ListResponse[T]],
        params: dict =...,
        headers: Optional[dict] =...,
        body: dict =...,
        files: dict =...,
        data_field: str =...,
    ) -> ListResponse[T]:
       ...

    @overload
    async def arequest(
        self,
        method: str,
        url: str,
        stream: Literal[False],
        cast: Type[FileHTTPResponse],
        params: dict =...,
        headers: Optional[dict] =...,
        body: dict =...,
        files: dict =...,
        data_field: str =...,
    ) -> FileHTTPResponse:
       ...

    @overload
    async def arequest(
        self,
        method: str,
        url: str,
        stream: Literal[False],
        cast: None,
        params: Optional[dict] =...,
        headers: Optional[dict] =...,
        body: Optional[dict] =...,
        files: Optional[dict] =...,
        data_field: str =...,
    ) -> None:
       ...

    @overload
    async def arequest(
        self,
        method: str,
        url: str,
        stream: Literal[True],
        cast: None,
        params: Optional[dict] =...,
        headers: Optional[dict] =...,
        body: Optional[dict] =...,
        files: Optional[dict] =...,
        data_field: str =...,
    ) -> AsyncIteratorHTTPResponse[str]:
       ...

    async def arequest(
        self,
        method: str,
        url: str,
        stream: Literal[True, False],
        cast: Union[Type[T], List[Type[T]], Type[ListResponse[T]], Type[FileHTTPResponse], None],
        params: Optional[dict] = None,
        headers: Optional[dict] =None,
        body: Optional[dict] =None,
        files: Optional[dict] =None,
        data_field: str = "data",
    ) -> Union[T, List[T], ListResponse[T], AsyncIteratorHTTPResponse[str], FileHTTPResponse, None]:
        """
        Send a request to the server.
        """
        method = method.upper()
        request = self.make_request(method, url, params=params, headers=headers, json=body, cast=cast, files=files,
                                    stream=stream
                                    )
        return await self.asend(request)

    async def asend(
        self,
        request: HTTPRequest,
    ) -> Union[T, List[T], ListResponse[T], AsyncIteratorHTTPResponse[str], FileHTTPResponse, None]:
        return self._parse_response(
            method=request.method,
            url=request.url,
            is_async=True,
            response=await self.a_session.request(
                request.method,
                request.url,
                params=request.params,
                headers=request.headers,

                json=request.json_body),
            cast=request.cast,
            stream=request.stream,
            data_field=request.data_field,
        )

    def _parse_response(
        self,
        method: str,
        url: str,
        stream: bool,
        response: [requests.Response, aiohttp.ClientResponse],
        cast: Union[Type[T], List[Type[T]], Type[ListResponse[T]], Type[FileHTTPResponse], None],
        data_field: str = "data",
        is_async: Literal[True, False] = False
    ) -> Union[
        T, List[T], ListResponse[T], IteratorHTTPResponse[str], AsyncIteratorHTTPResponse[str], FileHTTPResponse, None
    ]:
        resp_content_type = response.headers.get("content-type", "").lower()
        logid = response.headers.get("x-tt-logid")
        if "event-stream" in resp_content_type:
            if is_async:
                # return AsyncIteratorHTTPResponse(response, response.content.iter_any())
                return AsyncIteratorHTTPResponse(response, response.content.__aiter__())
            return IteratorHTTPResponse(response, response.iter_lines())

        if resp_content_type and "audio" in resp_content_type:
            return FileHTTPResponse(response)

        code, msg, data = self._parse_requests_code_msg(method, url, response, data_field)

        if code is not None and code > 0:
            # log_warning("request %s#%s failed, logid=%s, code=%s, msg=%s", method, url, logid, code, msg)
            raise AiAgentPlatformAPIError(code, msg, logid)
        elif code is None and msg!= "":
            # log_warning("request %s#%s failed, logid=%s, msg=%s", method, url, logid, msg)
            if msg in AiAgentPlatform_PKCE_AUTH_ERROR_TYPE_ENUMS:
                raise AiAgentPlatformPKCEAuthError(AiAgentPlatformPKCEAuthErrorType(msg), logid)
            raise AiAgentPlatformAPIError(code, msg, logid)
        if isinstance(cast, List):
            item_cast = cast[0]
            return [item_cast.model_validate(item) for item in data]
        elif hasattr(cast, "__origin__") and cast.__origin__ is ListResponse:  # type: ignore
            item_cast = get_args(cast)[0]
            return ListResponse(response, [item_cast.model_validate(item) for item in data])
        else:
            if cast is None:
                return None

            # res = cast.model_validate(data) if data is not None else cast()
            # if hasattr(res, "_raw_response"):
            #     res._raw_response = response
            return data

    def _parse_requests_code_msg(
        self, method: str, url: str, response: requests.Response, data_field: str = "data"
    ) -> Tuple[Optional[int], str, Any]:
        try:
            body = response.json()
            logid = response.headers.get("x-tt-logid")
            # log_debug("request %s#%s responding, logid=%s, data=%s", method, url, logid, body)
        except:
            raise AiAgentPlatformAPIError(
                response.status_code,
                response.text,
                response.headers.get("x-tt-logid"),
            )

        if "code" in body and "msg" in body and int(body["code"]) > 0:
            return int(body["code"]), body["msg"], body.get(data_field)
        if "error_code" in body and body["error_code"] in AiAgentPlatform_PKCE_AUTH_ERROR_TYPE_ENUMS:
            return None, body["error_code"], None
        if "error_message" in body and body["error_message"]!= "":
            return None, body["error_message"], None
        if data_field in body or "debug_url" in body:
            if "first_id" in body:
                return (
                    0,
                    "",
                    {
                        "first_id": body["first_id"],
                        "has_more": body["has_more"],
                        "last_id": body["last_id"],
                        "items": body["data"],
                    },
                )
            if "debug_url" in body:
                return (
                    0,
                    "",
                    {
                        "data": body.get(data_field),
                        "debug_url": body.get("debug_url") or "",
                        "execute_id": body.get("execute_id") or None,
                    },
                )
            return 0, "", body[data_field]
        if data_field == "data.data":
            return 0, "", body["data"]["data"]
        return 0, "", body