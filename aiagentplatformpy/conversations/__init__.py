from typing import Any, Dict, List, Optional

from aiagentplatformpy.auth import Auth
from aiagentplatformpy.model import AsyncNumberPaged, AiAgentPlatformModel, HTTPRequest, NumberPaged
from aiagentplatformpy.request import Requester
from aiagentplatformpy.util import remove_url_trailing_slash


class Conversation(AiAgentPlatformModel):
    id: str
    created_at: int
    meta_data: Dict[str, str]
    # section_id is used to distinguish the context sections of the session history. The same section is one context.
    last_section_id: str


class Section(AiAgentPlatformModel):
    id: str
    conversation_id: str


class _PrivateListConversationResp(AiAgentPlatformModel):
    has_more: bool
    conversations: List[Conversation]

    def get_total(self) -> Optional[int]:
        return None

    def get_has_more(self) -> Optional[bool]:
        return self.has_more

    def get_items(self) -> List[Conversation]:
        return self.conversations


class ConversationsClient(object):
    def __init__(self, base_url: str, auth: Auth, requester: Requester):
        self._base_url = remove_url_trailing_slash(base_url)
        self._auth = auth
        self._requester = requester
        self._messages = None

    def create(
        self,
        *,
        inputs=None,
        app_key: Optional[str] = None,
        user_id=None
    ) -> Conversation:
        """
        Create a conversation.
        Conversation is an interaction between a bot and a user, including one or more messages.
        returned when retrieving messages.
        :return: Conversation object
        """
        url = f"{self._base_url}/api/proxy/api/v1/create_conversation"
        body: Dict[str, Any] = {
            "Inputs": inputs,
            "UserID": user_id,
        }
        if app_key:
            body["AppKey"] = app_key
        return self._requester.request("post", url, False, Conversation, body=body)

    def update(
        self,
        *,
        inputs=None,
        app_key: Optional[str] = None,
        conversation_id: Optional[str] = None,
        user_id=None
    ) -> Conversation:
        """
        update a conversation.
        Conversation is an interaction between a bot and a user, including one or more messages.
        returned when retrieving messages.
        :return: Conversation object
        """
        url = f"{self._base_url}/api/proxy/api/v1/update_conversation"
        body: Dict[str, Any] = {
            "AppConversationID": conversation_id,
            "Inputs": inputs,
            "UserID": user_id,
        }
        if app_key:
            body["AppKey"] = app_key
        return self._requester.request("post", url, False, Conversation, body=body)

    # def list(
    #     self,
    #     *,
    #     app_key: str,
    #     page_num: int = 1,
    #     page_size: int = 50,
    # ):
    #     url = f"{self._base_url}/v1/conversations"
    #
    #     def request_maker(i_page_num: int, i_page_size: int) -> HTTPRequest:
    #         return self._requester.make_request(
    #             "GET",
    #             url,
    #             params={
    #                 "AppKey": app_key,
    #                 "page_num": i_page_num,
    #                 "page_size": i_page_size,
    #             },
    #             cast=_PrivateListConversationResp,
    #             is_async=False,
    #             stream=False,
    #         )
    #
    #     return NumberPaged(
    #         page_num=page_num,
    #         page_size=page_size,
    #         requestor=self._requester,
    #         request_maker=request_maker,
    #     )
    #
    # def retrieve(self, *, conversation_id: str) -> Conversation:
    #     """
    #     Get the information of specific conversation.
    #
    #     docs en: https://www.coze.com/docs/developer_guides/retrieve_conversation
    #     docs cn: https://www.coze.cn/docs/developer_guides/retrieve_conversation
    #
    #     :param conversation_id: The ID of the conversation.
    #     :return: Conversation object
    #     """
    #     url = f"{self._base_url}/v1/conversation/retrieve"
    #     params = {
    #         "conversation_id": conversation_id,
    #     }
    #     return self._requester.request("get", url, False, Conversation, params=params)
    #
    # def clear(self, *, conversation_id: str) -> Section:
    #     url = f"{self._base_url}/v1/conversations/{conversation_id}/clear"
    #     return self._requester.request("post", url, False, Section)
    #
    # @property
    # def messages(self):
    #     if not self._messages:
    #         from .message import MessagesClient
    #
    #         self._messages = MessagesClient(self._base_url, self._auth, self._requester)
    #     return self._messages


class AsyncConversationsClient(object):
    def __init__(self, base_url: str, auth: Auth, requester: Requester):
        self._base_url = remove_url_trailing_slash(base_url)
        self._auth = auth
        self._requester = requester
        self._messages = None

    async def create(
        self,
        *,
        inputs=None,
        app_key: Optional[str] = None,
        user_id=None
    ) -> Conversation:
        """
        Create a conversation.
        Conversation is an interaction between a bot and a user, including one or more messages.
        returned when retrieving messages.
        :return: Conversation object
        """
        url = f"{self._base_url}/api/proxy/api/v1/create_conversation"
        body: Dict[str, Any] = {
            "Inputs": inputs,
            "UserID": user_id,
        }
        if app_key:
            body["AppKey"] = app_key
        return self._requester.request("post", url, False, Conversation, body=body)
    async def update(
        self,
        *,
        inputs=None,
        app_key: Optional[str] = None,
        conversation_id: Optional[str] = None,
        user_id=None
    ) -> Conversation:
        """
        update a conversation.
        Conversation is an interaction between a bot and a user, including one or more messages.
        returned when retrieving messages.
        :return: Conversation object
        """
        url = f"{self._base_url}/api/proxy/api/v1/update_conversation"
        body: Dict[str, Any] = {
            "AppConversationID": conversation_id,
            "Inputs": inputs,
            "UserID": user_id,
        }
        if app_key:
            body["AppKey"] = app_key
        return self._requester.request("post", url, False, Conversation, body=body)

    # async def list(
    #     self,
    #     *,
    #     app_key: str,
    #     page_num: int = 1,
    #     page_size: int = 50,
    # ):
    #     url = f"{self._base_url}/v1/conversations"
    #
    #     def request_maker(i_page_num: int, i_page_size: int) -> HTTPRequest:
    #         return self._requester.make_request(
    #             "GET",
    #             url,
    #             params={
    #                 "AppKey": app_key,
    #                 "page_num": i_page_num,
    #                 "page_size": i_page_size,
    #             },
    #             cast=_PrivateListConversationResp,
    #             is_async=False,
    #             stream=False,
    #         )
    #
    #     return await AsyncNumberPaged.build(
    #         page_num=page_num,
    #         page_size=page_size,
    #         requestor=self._requester,
    #         request_maker=request_maker,
    #     )
    #
    # async def retrieve(self, *, conversation_id: str) -> Conversation:
    #     """
    #     Get the information of specific conversation.
    #
    #     docs en: https://www.coze.com/docs/developer_guides/retrieve_conversation
    #     docs cn: https://www.coze.cn/docs/developer_guides/retrieve_conversation
    #
    #     :param conversation_id: The ID of the conversation.
    #     :return: Conversation object
    #     """
    #     url = f"{self._base_url}/v1/conversation/retrieve"
    #     params = {
    #         "conversation_id": conversation_id,
    #     }
    #     return await self._requester.arequest("get", url, False, Conversation, params=params)
    #
    # async def clear(self, *, conversation_id: str) -> Section:
    #     url = f"{self._base_url}/v1/conversations/{conversation_id}/clear"
    #     return await self._requester.arequest("post", url, False, Section)
    #
    # @property
    # def messages(self):
    #     if not self._messages:
    #         from .message import AsyncMessagesClient
    #
    #         self._messages = AsyncMessagesClient(self._base_url, self._auth, self._requester)
    #     return self._messages
