from typing import TYPE_CHECKING, Optional

from aiagentplatformpy.auth import Auth
from aiagentplatformpy.config import AiAgentPlatform_COM_BASE_URL
from aiagentplatformpy.request import Requester
from aiagentplatformpy.util import remove_url_trailing_slash

if TYPE_CHECKING:
    from .chat import AsyncChatClient, ChatClient
    from .conversations import AsyncConversationsClient, ConversationsClient
    # from .knowledge import AsyncKnowledgeClient, KnowledgeClient


class AiAgentPlatform(object):
    def __init__(
        self,
        auth: Auth,
        base_url: str = AiAgentPlatform_COM_BASE_URL,
        # http_client: Optional[SyncHTTPClient] = None,
    ):
        self._auth = auth
        self._base_url = remove_url_trailing_slash(base_url)
        self._requester = Requester(auth=auth)

        # service client
        self._conversations: Optional[ConversationsClient] = None
        self._chat: Optional[ChatClient] = None
        # self._knowledge: Optional[KnowledgeClient] = None  # deprecated

    @property
    def conversations(self) -> "ConversationsClient":
        if not self._conversations:
            from .conversations import ConversationsClient

            self._conversations = ConversationsClient(self._base_url, self._auth, self._requester)
        return self._conversations

    @property
    def chat(self) -> "ChatClient":
        if not self._chat:
            from aiagentplatformpy.chat import ChatClient

            self._chat = ChatClient(self._base_url, self._auth, self._requester)
        return self._chat

    # @property
    # def knowledge(self) -> "KnowledgeClient":
    #     warnings.warn(
    #         "The 'coze.knowledge' module is deprecated and will be removed in a future version. "
    #         "Please use 'coze.datasets' instead.",
    #         DeprecationWarning,
    #         stacklevel=2,
    #     )
    #     if not self._knowledge:
    #         from .knowledge import KnowledgeClient
    #
    #         self._knowledge = KnowledgeClient(self._base_url, self._auth, self._requester)
    #     return self._knowledge


class AsyncAiAgentPlatform(object):
    def __init__(
        self,
        auth: Auth,
        base_url: str = AiAgentPlatform_COM_BASE_URL,
        # http_client: Optional[AsyncHTTPClient] = None,
    ):
        self._auth = auth
        self._base_url = remove_url_trailing_slash(base_url)
        self._requester = Requester(auth=auth)

        # service client
        self._chat: Optional[AsyncChatClient] = None
        self._conversations: Optional[AsyncConversationsClient] = None
        # self._knowledge: Optional[AsyncKnowledgeClient] = None  # deprecated

    @property
    def chat(self) -> "AsyncChatClient":
        if not self._chat:
            from aiagentplatformpy.chat import AsyncChatClient

            self._chat = AsyncChatClient(self._base_url, self._auth, self._requester)
        return self._chat

    @property
    def conversations(self) -> "AsyncConversationsClient":
        if not self._conversations:
            from .conversations import AsyncConversationsClient

            self._conversations = AsyncConversationsClient(self._base_url, self._auth, self._requester)
        return self._conversations

    # @property
    # def knowledge(self) -> "AsyncKnowledgeClient":
    #     warnings.warn(
    #         "The 'coze.knowledge' module is deprecated and will be removed in a future version. "
    #         "Please use 'coze.datasets' instead.",
    #         DeprecationWarning,
    #         stacklevel=2,
    #     )
    #     if not self._knowledge:
    #         from .knowledge import AsyncKnowledgeClient
    #
    #         self._knowledge = AsyncKnowledgeClient(self._base_url, self._auth, self._requester)
    #     return self._knowledge
