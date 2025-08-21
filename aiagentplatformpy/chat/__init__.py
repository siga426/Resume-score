import contextlib
import json
from enum import Enum
from typing import TYPE_CHECKING, AsyncIterator, Dict, List, Optional, Union, overload

import aiohttp

from aiagentplatformpy.auth import Auth
from aiagentplatformpy.model import AsyncIteratorHTTPResponse, AsyncStream, AiAgentPlatformModel, IteratorHTTPResponse, ListResponse, Stream
from aiagentplatformpy.request import Requester
from aiagentplatformpy.util import remove_url_trailing_slash

if TYPE_CHECKING:
    from .message import AsyncChatMessagesClient, ChatMessagesClient


class MessageRole(str, Enum):
    # Indicates that the content of the message is sent by the user.
    USER = "user"

    # Indicates that the content of the message is sent by the bot.
    ASSISTANT = "assistant"


class MessageType(str, Enum):
    # User input content.
    # 用户输入内容。
    QUESTION = "question"

    # The message content returned by the Bot to the user, supporting incremental return. If the workflow is bound to a message node, there may be multiple answer scenarios, and the end flag of the streaming return can be used to determine that all answers are completed.
    # Bot 返回给用户的消息内容，支持增量返回。如果工作流绑定了消息节点，可能会存在多 answer 场景，此时可以用流式返回的结束标志来判断所有 answer 完成。
    ANSWER = "answer"

    # Intermediate results of the function (function call) called during the Bot conversation process.
    # Bot 对话过程中调用函数（function call）的中间结果。
    FUNCTION_CALL = "function_call"

    # Results returned after calling the tool (function call).
    # 调用工具 （function call）后返回的结果。
    TOOL_OUTPUT = "tool_output"

    # Results returned after calling the tool (function call).
    # 调用工具 （function call）后返回的结果。
    TOOL_RESPONSE = "tool_response"

    # If the user question suggestion switch is turned on in the Bot configuration, the reply content related to the recommended questions will be returned.
    # 如果在 Bot 上配置打开了用户问题建议开关，则会返回推荐问题相关的回复内容。不支持在请求中作为入参。
    FOLLOW_UP = "follow_up"

    # In the scenario of multiple answers, the server will return a verbose package, and the corresponding content is in JSON format. content.msg_type = generate_answer_finish represents that all answers have been replied to.
    # 多 answer 场景下，服务端会返回一个 verbose 包，对应的 content 为 JSON 格式，content.msg_type =generate_answer_finish 代表全部 answer 回复完成。不支持在请求中作为入参。
    VERBOSE = "verbose"

    UNKNOWN = ""


class MessageContentType(str, Enum):
    # Text.
    # 文本。
    TEXT = "text"

    # Multimodal content, that is, a combination of text and files, or a combination of text and images.
    # 多模态内容，即文本和文件的组合、文本和图片的组合。
    OBJECT_STRING = "object_string"

    # message card. This enum value only appears in the interface response and is not supported as an input parameter.
    # 卡片。此枚举值仅在接口响应中出现，不支持作为入参。
    CARD = "card"

    # If there is a voice message in the input message, the conversation.audio.delta event will be returned in the
    # streaming response event. The data of this event corresponds to the Message Object. The content_type is audio,
    # and the content is a PCM audio clip with a sampling rate of 24kHz, raw 16 bit, 1 channel, little-endian.
    # 如果入参的消息中有语音消息，那么流式响应事件中，会返回 conversation.audio.delta 事件，此事件的 data 对应 Message Object。
    # content_type 为 audio，content 为采样率 24kHz，raw 16 bit, 1 channel, little-endian 的 pcm 音频片段。
    AUDIO = "audio"


class MessageObjectStringType(str, Enum):
    """
    The content type of the multimodal message.
    """

    TEXT = "text"
    FILE = "file"
    IMAGE = "image"
    AUDIO = "audio"


class MessageObjectString(AiAgentPlatformModel):
    # The content type of the multimodal message.
    # 多模态消息内容类型
    type: MessageObjectStringType
    # Text content. Required when type is text.
    # 文本内容。
    text: Optional[str] = None
    # The ID of the file or image content.
    # 在 type 为 file 或 image 时，file_id 和 file_url 应至少指定一个。
    file_id: Optional[str] = None
    # The online address of the file or image content.<br>Must be a valid address that is publicly accessible.
    # file_id or file_url must be specified when type is file or image.
    # 文件或图片内容的在线地址。必须是可公共访问的有效地址。
    # 在 type 为 file 或 image 时，file_id 和 file_url 应至少指定一个。
    file_url: Optional[str] = None

    @staticmethod
    def build_text(text: str):
        return MessageObjectString(type=MessageObjectStringType.TEXT, text=text)

    @staticmethod
    def build_image(file_id: Optional[str] = None, file_url: Optional[str] = None):
        if not file_id and not file_url:
            raise ValueError("file_id or file_url must be specified")

        return MessageObjectString(type=MessageObjectStringType.IMAGE, file_id=file_id, file_url=file_url)

    @staticmethod
    def build_file(file_id: Optional[str] = None, file_url: Optional[str] = None):
        if not file_id and not file_url:
            raise ValueError("file_id or file_url must be specified")

        return MessageObjectString(type=MessageObjectStringType.FILE, file_id=file_id, file_url=file_url)

    @staticmethod
    def build_audio(file_id: Optional[str] = None, file_url: Optional[str] = None):
        if not file_id and not file_url:
            raise ValueError("file_id or file_url must be specified")

        return MessageObjectString(type=MessageObjectStringType.AUDIO, file_id=file_id, file_url=file_url)


class Message(AiAgentPlatformModel):
    # The entity that sent this message.
    # role: MessageRole
    # The type of message.
    # type: MessageType = MessageType.UNKNOWN
    # The content of the message. It supports various types of content, including plain text, multimodal (a mix of text, images, and files), message cards, and more.
    # 消息的内容，支持纯文本、多模态（文本、图片、文件混合输入）、卡片等多种类型的内容。
    # content: str
    # The type of message content.
    # 消息内容的类型
    # content_type: MessageContentType
    # Additional information when creating a message, and this additional information will also be returned when retrieving messages.
    # Custom key-value pairs should be specified in Map object format, with a length of 16 key-value pairs. The length of the key should be between 1 and 64 characters, and the length of the value should be between 1 and 512 characters.
    # 创建消息时的附加消息，获取消息时也会返回此附加消息。
    # 自定义键值对，应指定为 Map 对象格式。长度为 16 对键值对，其中键（key）的长度范围为 1～64 个字符，值（value）的长度范围为 1～512 个字符。
    meta_data: Optional[Dict[str, str]] = None

    id: Optional[str] = None
    conversation_id: Optional[str] = None
    # section_id is used to distinguish the context sections of the session history. The same section is one context.
    section_id: Optional[str] = None
    chat_id: Optional[str] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    task_id: str = None
    answer: str = None
    event: str = None

    @staticmethod
    def build_user_question_text(content: str, meta_data: Optional[Dict[str, str]] = None) -> "Message":
        return Message(
            role=MessageRole.USER,
            type=MessageType.QUESTION,
            content=content,
            content_type=MessageContentType.TEXT,
            meta_data=meta_data,
        )

    @staticmethod
    def build_user_question_objects(
        objects: List[MessageObjectString], meta_data: Optional[Dict[str, str]] = None
    ) -> "Message":
        return Message(
            role=MessageRole.USER,
            type=MessageType.QUESTION,
            content=json.dumps([obj.model_dump() for obj in objects]),
            content_type=MessageContentType.OBJECT_STRING,
            meta_data=meta_data,
        )

    @staticmethod
    def build_assistant_answer(content: str, meta_data: Optional[Dict[str, str]] = None) -> "Message":
        return Message(
            role=MessageRole.ASSISTANT,
            type=MessageType.ANSWER,
            content=content,
            content_type=MessageContentType.TEXT,
            meta_data=meta_data,
        )


class ChatStatus(str, Enum):
    """
    The running status of the session
    """

    # The session has been created.
    CREATED = "created"

    # The Bot is processing.
    IN_PROGRESS = "in_progress"

    # The Bot has finished processing, and the session has ended.
    COMPLETED = "completed"

    # The session has failed.
    FAILED = "failed"

    # The session is interrupted and requires further processing.
    REQUIRES_ACTION = "requires_action"

    # The session is canceled.
    CANCELED = "canceled"


class ChatError(AiAgentPlatformModel):
    # The error code. An integer type. 0 indicates success, other values indicate failure.
    code: int
    # The error message. A string type.
    msg: str


class ChatRequiredActionType(str, Enum):
    UNKNOWN = ""
    SUBMIT_TOOL_OUTPUTS = "submit_tool_outputs"


class ChatToolCallType(str, Enum):
    FUNCTION = "function"


class ChatToolCallFunction(AiAgentPlatformModel):
    # The name of the method.
    name: str

    # The parameters of the method.
    arguments: str


class ChatToolCall(AiAgentPlatformModel):
    # The ID for reporting the running results.
    id: str

    # The type of tool, with the enum value of function.
    type: ChatToolCallType

    # The definition of the execution method function.
    function: Optional[ChatToolCallFunction] = None


class ChatSubmitToolOutputs(AiAgentPlatformModel):
    # Details of the specific reported information.
    tool_calls: List[ChatToolCall]


class ChatRequiredAction(AiAgentPlatformModel):
    """Details of the information needed for execution."""

    # The type of additional operation, with the enum value of submit_tool_outputs.
    type: ChatRequiredActionType

    # Details of the results that need to be submitted, uploaded through the submission API, and
    # the chat can continue afterward.
    submit_tool_outputs: Optional[ChatSubmitToolOutputs] = None


class ChatUsage(AiAgentPlatformModel):
    # The total number of Tokens consumed in this chat, including the consumption for both the input
    # and output parts.
    token_count: int

    # The total number of Tokens consumed for the output part.
    output_count: int

    # The total number of Tokens consumed for the input part.
    input_count: int


class Chat(AiAgentPlatformModel):
    # The ID of the chat.
    id: str
    task_id: str
    # The ID of the conversation.
    conversation_id: str
    # answer: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    start_time_first_resp: Optional[int] = None
    latency_first_resp: Optional[int] = None
    latency: Optional[float] = None
    created_at: Optional[float] = None
    event: str = None


class Knowledge(AiAgentPlatformModel):
    # The ID of the chat.
    id: str
    task_id: str
    # The ID of the conversation.
    conversation_id: str
    # answer: str
    message_id: str = None
    docs: Optional[dict] = None
    latency: Optional[float] = None
    created_at: Optional[float] = None
    event: str = None


class ChatPoll(AiAgentPlatformModel):
    chat: Chat
    messages: Optional[ListResponse[Message]] = None
    # messages = None


class ChatEventType(str, Enum):
    # Event for creating a conversation, indicating the start of the conversation.
    # 创建对话的事件，表示对话开始。
    CONVERSATION_CHAT_START = "message_start"

    CONVERSATION_CHAT_OUTPUT_START = "message_output_start"

    CONVERSATION_CHAT_OUTPUT_END = "message_output_end"

    CONVERSATION_CHAT_IN_MESSAGE = "message"

    CONVERSATION_KNOWLEDGE_RETRIEVE = "knowledge_retrieve"

    CONVERSATION_KNOWLEDGE_RETRIEVE_END = "knowledge_retrieve_end"

    # Incremental message, usually an incremental message when type=answer.
    # 增量消息，通常是 type=answer 时的增量消息。
    CONVERSATION_MESSAGE_COST = "message_cost"

    # This event is used to mark a failed conversation.
    # 此事件用于标识对话失败。
    CONVERSATION_CHAT_FAILED = "conversation.chat.failed"

    CONVERSATION_CHAT_ANSWER = "text"

    # Error events during the streaming response process. For detailed explanations of code and msg, please refer to Error codes.
    # 流式响应过程中的错误事件。关于 code 和 msg 的详细说明，可参考错误码。
    ERROR = "error"

    # The streaming response for this session ended normally.
    # 本次会话的流式返回正常结束。
    DONE = "message_end"


class ChatEvent(AiAgentPlatformModel):
    # logid: str
    event: str
    chat: Optional[Chat] = None
    message: Optional[Message] = None
    knowledge: Optional[Knowledge] = None


def _chat_stream_handler(data: Dict, raw_response, is_async: bool = False) -> ChatEvent:
    event = data["event"]
    event_data = data["data:data"]
    _event = json.loads(event_data)['event']
    if _event == ChatEventType.ERROR:
        raise Exception(f"error event: {event_data}")  # TODO: error struct format
    elif _event in [
        ChatEventType.CONVERSATION_CHAT_IN_MESSAGE,
        ChatEventType.DONE
    ]:
        event = ChatEvent(event=_event, message=Message.model_validate_json(event_data))
        event._raw_response = raw_response
        return event
    elif _event in [
        ChatEventType.CONVERSATION_CHAT_START,
        ChatEventType.CONVERSATION_CHAT_OUTPUT_START,
        ChatEventType.CONVERSATION_MESSAGE_COST,
        ChatEventType.CONVERSATION_CHAT_OUTPUT_END
    ]:
        event = ChatEvent(event=_event, chat=Chat.model_validate_json(event_data))
        event._raw_response = raw_response
        return event
    elif _event in [ChatEventType.CONVERSATION_KNOWLEDGE_RETRIEVE_END, ChatEventType.CONVERSATION_KNOWLEDGE_RETRIEVE]:
        event = ChatEvent(event=_event, knowledge=Knowledge.model_validate_json(event_data))
        event._raw_response = raw_response
        return event
    else:
        event = ChatEvent(event=_event)
        event._raw_response = raw_response
        return event
        #raise ValueError(f"invalid chat.event: {_event}, {data}")


def _sync_chat_stream_handler(data: Dict, raw_response) -> ChatEvent:
    return _chat_stream_handler(data, raw_response=raw_response, is_async=False)


def _async_chat_stream_handler(data: Dict, raw_response) -> ChatEvent:
    return _chat_stream_handler(data, raw_response=raw_response, is_async=True)


class ToolOutput(AiAgentPlatformModel):
    # The ID for reporting the running results. You can get this ID under the tool_calls field in response of the Chat
    # API.
    tool_call_id: str

    # The execution result of the tool.
    output: str


class ChatClient(object):
    def __init__(self, base_url: str, auth: Auth, requester: Requester):
        self._base_url = remove_url_trailing_slash(base_url)
        self._auth = auth
        self._requester = requester
        self._messages: Optional[ChatMessagesClient] = None

    def create(
        self,
        *,
        user_id: str,
        conversation_id: Optional[str] = None,
        query: str,
        query_extend: Optional[List[Message]] = None
    ) -> Chat:
        """
        Call the Chat API with non-streaming to send messages to a published AiAgentPlatform bot.

        docs en: https://www.coze.com/docs/developer_guides/chat_v3
        docs zh: https://www.coze.cn/docs/developer_guides/chat_v3

        :param user_id: The user who calls the API to chat with the bot.
        This parameter is defined, generated, and maintained by the user within their business system.
        :param conversation_id: Indicate which conversation the chat is taking place in.
        :param query: question
        :param query_extend: Additional information for the conversation. You can pass the user's query for this
        conversation through this field. The array length is limited to 100, meaning up to 100 messages can be input.
        :return: chat object
        """
        res = self._create(
            user_id=user_id,
            stream=False,
            query=query,
            query_extend=query_extend,
            conversation_id=conversation_id,
        )
        for i in res:
            if i.event == ChatEventType.DONE:
                return i.message

    @contextlib.contextmanager
    def stream(
        self,
        *,
        user_id: str,
        conversation_id: Optional[str] = None,
        query: str,
        query_extend: Optional[List[Message]] = None,
        **kwargs,
    ) -> Stream[ChatEvent]:
        """
        Call the Chat API with streaming to send messages to a published AiAgentPlatform bot.

        docs en: https://www.coze.com/docs/developer_guides/chat_v3
        docs zh: https://www.coze.cn/docs/developer_guides/chat_v3


        :param user_id: The user who calls the API to chat with the bot.
        This parameter is defined, generated, and maintained by the user within their business system.
        :param conversation_id: Indicate which conversation the chat is taking place in.
        :param query: question
        :param query_extend: Additional information for the conversation. You can pass the user's query for this
        conversation through this field. The array length is limited to 100, meaning up to 100 messages can be input.
        :return: iterator of ChatEvent
        """
        yield self._create(
            user_id=user_id,
            stream=True,
            query=query,
            query_extend=query_extend,
            conversation_id=conversation_id,
            headers={'Accept': 'text/event-stream'},
            **kwargs,
        )

    # def create_and_poll(
    #     self,
    #     *,
    #     bot_id: str,
    #     user_id: str,
    #     conversation_id: Optional[str] = None,
    #     additional_messages: Optional[List[Message]] = None,
    #     custom_variables: Optional[Dict[str, str]] = None,
    #     auto_save_history: bool = True,
    #     meta_data: Optional[Dict[str, str]] = None,
    #     poll_timeout: Optional[int] = None,
    # ) -> ChatPoll:
    #     """
    #     Call the Chat API with non-streaming to send messages to a published AiAgentPlatform bot and
    #     fetch chat status & message.
    #
    #     docs en: https://www.coze.com/docs/developer_guides/chat_v3
    #     docs zh: https://www.coze.cn/docs/developer_guides/chat_v3
    #
    #     :param bot_id: The ID of the bot that the API interacts with.
    #     :param user_id: The user who calls the API to chat with the bot.
    #     This parameter is defined, generated, and maintained by the user within their business system.
    #     :param conversation_id: Indicate which conversation the chat is taking place in.
    #     :param additional_messages: Additional information for the conversation. You can pass the user's query for this
    #     conversation through this field. The array length is limited to 100, meaning up to 100 messages can be input.
    #     :param custom_variables: The customized variable in a key-value pair.
    #     :param auto_save_history: Whether to automatically save the history of conversation records.
    #     :param meta_data: Additional information, typically used to encapsulate some business-related fields.
    #     :param poll_timeout: poll timeout in seconds
    #     :return: chat object
    #     """
    #     chat = self.create(
    #         bot_id=bot_id,
    #         user_id=user_id,
    #         conversation_id=conversation_id,
    #         additional_messages=additional_messages,
    #         custom_variables=custom_variables,
    #         auto_save_history=auto_save_history,
    #         meta_data=meta_data,
    #     )
    #
    #     start = int(time.time())
    #     interval = 1
    #     while chat.status == ChatStatus.IN_PROGRESS:
    #         if poll_timeout is not None and int(time.time()) - start > poll_timeout:
    #             # too long, cancel chat
    #             self.cancel(conversation_id=chat.conversation_id, chat_id=chat.id)
    #             return ChatPoll(chat=chat)
    #
    #         time.sleep(interval)
    #         chat = self.retrieve(conversation_id=chat.conversation_id, chat_id=chat.id)
    #
    #     messages = self.messages.list(conversation_id=chat.conversation_id, chat_id=chat.id)
    #     return ChatPoll(chat=chat, messages=messages)

    @overload
    def _create(
        self,
        *,
        user_id: str,
        conversation_id: Optional[str] = None,
        stream: bool,
        query: str,
        query_extend: Optional[List[Message]] = None,
    ) -> Stream[ChatEvent]: ...

    @overload
    def _create(
        self,
        *,
        user_id: str,
        conversation_id: Optional[str] = None,
        stream: bool,
        query: str,
        query_extend: Optional[List[Message]] = None,
    ) -> Chat: ...

    def _create(
        self,
        *,
        user_id: str,
        conversation_id: Optional[str] = None,
        stream: bool,
        query: str,
        query_extend: Optional[List[Message]] = None,
        **kwargs,
    ) -> Union[Chat, Stream[ChatEvent]]:
        """
        Create a conversation.
        Conversation is an interaction between a bot and a user, including one or more messages.
        """
        url = f"{self._base_url}/api/proxy/api/v1/chat_query"
        body = {
            "AppConversationID": conversation_id,
            "UserID": user_id,
            "query": query,
            "ResponseMode": "streaming" if stream else "blocking",
        }
        if query_extend:
            body['QueryExtends'] = query_extend
        headers: Optional[dict] = kwargs.get("headers")
        if not stream:
            resp = self._requester.request(
                "post",
                url,
                False,
                Chat,
                headers=headers,
                body=body,
            )
            return Stream(resp._raw_response, resp.data, fields=["event", "data:data"], handler=_sync_chat_stream_handler)

        response: IteratorHTTPResponse[str] = self._requester.request(
            "post",
            url,
            True,
            None,
            headers=headers,
            body=body,
        )
        return Stream(
            response._raw_response,
            response.data,
            fields=["event", "data:data"],
            handler=_sync_chat_stream_handler,
        )

    # def retrieve(
    #     self,
    #     *,
    #     conversation_id: str,
    #     chat_id: str,
    # ) -> Chat:
    #     """
    #     Get the detailed information of the chat.
    #
    #     docs en: https://www.coze.com/docs/developer_guides/retrieve_chat
    #     docs zh: https://www.coze.cn/docs/developer_guides/retrieve_chat
    #
    #     :param conversation_id: The ID of the conversation.
    #     :param chat_id: The ID of the chat.
    #     :return: chat object
    #     """
    #     url = f"{self._base_url}/v3/chat/retrieve"
    #     params = {
    #         "conversation_id": conversation_id,
    #         "chat_id": chat_id,
    #     }
    #     return self._requester.request("post", url, False, Chat, params=params)

    # def submit_tool_outputs(
    #     self, *, conversation_id: str, chat_id: str, tool_outputs: List[ToolOutput], stream: bool
    # ) -> Union[Chat, Stream[ChatEvent]]:
    #     """
    #     Call this API to submit the results of tool execution.
    #
    #     docs en: https://www.coze.com/docs/developer_guides/chat_submit_tool_outputs
    #     docs zh: https://www.coze.cn/docs/developer_guides/chat_submit_tool_outputs
    #
    #     :param conversation_id: The Conversation ID can be viewed in the 'conversation_id' field of the Response when
    #     initiating a conversation through the Chat API.
    #     :param chat_id: The Chat ID can be viewed in the 'id' field of the Response when initiating a chat through the
    #     Chat API. If it is a streaming response, check the 'id' field in the chat event of the Response.
    #     :param tool_outputs: The execution result of the tool. For detailed instructions, refer to the ToolOutput Object
    #     :param stream: Whether to enable streaming response.
    #     true: Fill in the context of the previous conversation and continue with streaming response.
    #     false: (Default) Non-streaming response, only reply with basic information of the conversation.
    #     :return:
    #     """
    #     url = f"{self._base_url}/v3/chat/submit_tool_outputs"
    #     params = {
    #         "conversation_id": conversation_id,
    #         "chat_id": chat_id,
    #     }
    #     body = {
    #         "tool_outputs": [i.model_dump() for i in tool_outputs],
    #         "stream": stream,
    #     }
    #
    #     if not stream:
    #         return self._requester.request(
    #             "post",
    #             url,
    #             False,
    #             Chat,
    #             params=params,
    #             body=body,
    #         )
    #
    #     resp: IteratorHTTPResponse[str] = self._requester.request(
    #         "post",
    #         url,
    #         True,
    #         None,
    #         params=params,
    #         body=body,
    #     )
    #     return Stream(resp._raw_response, resp.data, fields=["event", "data"], handler=_sync_chat_stream_handler)

    def cancel(
        self,
        *,
        conversation_id: str,
        chat_id: str,
    ) -> Chat:
        """
        Call this API to cancel an ongoing chat.

        docs en: https://www.coze.com/docs/developer_guides/chat_cancel
        docs zh: https://www.coze.cn/docs/developer_guides/chat_cancel

        :param conversation_id: The Conversation ID can be viewed in the 'conversation_id' field of the Response when
        initiating a conversation through the Chat API.
        :param chat_id: The Chat ID can be viewed in the 'id' field of the Response when initiating a chat through the
        Chat API. If it is a streaming response, check the 'id' field in the chat event of the Response.
        :return:
        """
        url = f"{self._base_url}/v3/chat/cancel"
        body = {
            "conversation_id": conversation_id,
            "chat_id": chat_id,
        }
        return self._requester.request("post", url, False, Chat, body=body)

    # @property
    # def messages(
    #     self,
    # ) -> "ChatMessagesClient":
    #     if self._messages is None:
    #         from .message import ChatMessagesClient
    #
    #         self._messages = ChatMessagesClient(self._base_url, self._auth, self._requester)
    #     return self._messages


class AsyncChatClient(object):
    def __init__(self, base_url: str, auth: Auth, requester: Requester):
        self._base_url = remove_url_trailing_slash(base_url)
        self._auth = auth
        self._requester = requester
        self._messages: Optional[AsyncChatMessagesClient] = None

    async def create(
        self,
        *,
        user_id: str,
        conversation_id: Optional[str] = None,
        query: str,
        query_extend: Optional[List[Message]] = None
    ) -> Chat:
        """
        Call the Chat API with non-streaming to send messages to a published AiAgentPlatform bot.

        docs en: https://www.coze.com/docs/developer_guides/chat_v3
        docs zh: https://www.coze.cn/docs/developer_guides/chat_v3

        :param user_id: The user who calls the API to chat with the bot.
        This parameter is defined, generated, and maintained by the user within their business system.
        :param conversation_id: Indicate which conversation the chat is taking place in.
        :param query: question
        :param query_extend: Additional information for the conversation. You can pass the user's query for this
        conversation through this field. The array length is limited to 100, meaning up to 100 messages can be input.
        :return: chat object
        """
        try:
            self._requester.a_session = aiohttp.ClientSession()
            res = await self._create(
                user_id=user_id,
                stream=False,
                query=query,
                query_extend=query_extend,
                conversation_id=conversation_id,
            )
            async for i in res:
                if i.event == ChatEventType.DONE:
                    return i.message
        finally:
            try:
                if self._requester.a_session:
                    await self._requester.a_session.close()
            except:
                pass

    @contextlib.asynccontextmanager
    async def stream(
        self,
        *,
        user_id: str,
        conversation_id: Optional[str] = None,
        query: str,
        query_extend: Optional[List[Message]] = None,
        **kwargs,
    ) -> AsyncIterator[ChatEvent]:
        """
        Call the Chat API with streaming to send messages to a published AiAgentPlatform bot.

        docs en: https://www.coze.com/docs/developer_guides/chat_v3
        docs zh: https://www.coze.cn/docs/developer_guides/chat_v3


        :param user_id: The user who calls the API to chat with the bot.
        This parameter is defined, generated, and maintained by the user within their business system.
        :param conversation_id: Indicate which conversation the chat is taking place in.
        :param query: question
        :param query_extend: Additional information for the conversation. You can pass the user's query for this
        conversation through this field. The array length is limited to 100, meaning up to 100 messages can be input.
        :return: iterator of ChatEvent
        """
        # session = aiohttp.ClientSession()
        try:
            self._requester.a_session = aiohttp.ClientSession()
            yield await self._create(
                user_id=user_id,
                stream=True,
                query=query,
                query_extend=query_extend,
                conversation_id=conversation_id,
                headers={'Accept': 'text/event-stream'},
                **kwargs,
            )
        except:
            pass
        finally:
            try:
                if self._requester.a_session:
                    await self._requester.a_session.close()
            except:
                pass


    @overload
    async def _create(
        self,
        *,
        user_id: str,
        conversation_id: Optional[str] = None,
        stream: bool,
        query: str,
        query_extend: Optional[List[Message]] = None,
    ) -> AsyncStream[ChatEvent]: ...

    @overload
    async def _create(
        self,
        *,
        user_id: str,
        conversation_id: Optional[str] = None,
        stream: bool,
        query: str,
        query_extend: Optional[List[Message]] = None,
    ) -> Chat: ...

    async def _create(
        self,
        *,
        user_id: str,
        conversation_id: Optional[str] = None,
        stream: bool,
        query: str,
        query_extend: Optional[List[Message]] = None,
        **kwargs,
    ) -> Union[Chat, AsyncStream[ChatEvent]]:
        """
        Create a conversation.
        Conversation is an interaction between a bot and a user, including one or more messages.
        """
        url = f"{self._base_url}/api/proxy/api/v1/chat_query"
        body = {
            "AppConversationID": conversation_id,
            "UserID": user_id,
            "query": query,
            "ResponseMode": "streaming" if stream else "blocking",
        }
        if query_extend:
            body['QueryExtends'] = query_extend
        headers: Optional[dict] = kwargs.get("headers")
        if not stream:
            resp = await self._requester.arequest(
                "post",
                url,
                False,
                Chat,
                headers=headers,
                body=body
            )
            return AsyncStream(resp.data, fields=["event", "data:data"], handler=_async_chat_stream_handler, raw_response=resp._raw_response)

        resp: AsyncIteratorHTTPResponse[str] = await self._requester.arequest(
            "post",
            url,
            True,
            None,
            headers=headers,
            body=body
        )

        return AsyncStream(
            resp.data, fields=["event", "data:data"], handler=_async_chat_stream_handler, raw_response=resp._raw_response
        )

    # async def retrieve(
    #     self,
    #     *,
    #     conversation_id: str,
    #     chat_id: str,
    # ) -> Chat:
    #     """
    #     Get the detailed information of the chat.
    #
    #     docs en: https://www.coze.com/docs/developer_guides/retrieve_chat
    #     docs zh: https://www.coze.cn/docs/developer_guides/retrieve_chat
    #
    #     :param conversation_id: The ID of the conversation.
    #     :param chat_id: The ID of the chat.
    #     :return: chat object
    #     """
    #     url = f"{self._base_url}/v3/chat/retrieve"
    #     params = {
    #         "conversation_id": conversation_id,
    #         "chat_id": chat_id,
    #     }
    #     return await self._requester.arequest("post", url, False, Chat, params=params)
    #
    # async def submit_tool_outputs(self, *, conversation_id: str, chat_id: str, tool_outputs: List[ToolOutput]) -> Chat:
    #     """
    #     Call this API to submit the results of tool execution.
    #
    #     docs en: https://www.coze.com/docs/developer_guides/chat_submit_tool_outputs
    #     docs zh: https://www.coze.cn/docs/developer_guides/chat_submit_tool_outputs
    #
    #     :param conversation_id: The Conversation ID can be viewed in the 'conversation_id' field of the Response when
    #     initiating a conversation through the Chat API.
    #     :param chat_id: The Chat ID can be viewed in the 'id' field of the Response when initiating a chat through the
    #     Chat API. If it is a streaming response, check the 'id' field in the chat event of the Response.
    #     :param tool_outputs: The execution result of the tool. For detailed instructions, refer to the ToolOutput Object
    #     true: Fill in the context of the previous conversation and continue with streaming response.
    #     false: (Default) Non-streaming response, only reply with basic information of the conversation.
    #     :return:
    #     """
    #
    #     return await self._submit_tool_outputs(
    #         conversation_id=conversation_id, chat_id=chat_id, stream=False, tool_outputs=tool_outputs
    #     )
    #
    # async def submit_tool_outputs_stream(
    #     self,
    #     *,
    #     conversation_id: str,
    #     chat_id: str,
    #     tool_outputs: List[ToolOutput],
    # ) -> AsyncIterator[ChatEvent]:
    #     """
    #     Call this API to submit the results of tool execution.
    #
    #     docs en: https://www.coze.com/docs/developer_guides/chat_submit_tool_outputs
    #     docs zh: https://www.coze.cn/docs/developer_guides/chat_submit_tool_outputs
    #
    #     :param conversation_id: The Conversation ID can be viewed in the 'conversation_id' field of the Response when
    #     initiating a conversation through the Chat API.
    #     :param chat_id: The Chat ID can be viewed in the 'id' field of the Response when initiating a chat through the
    #     Chat API. If it is a streaming response, check the 'id' field in the chat event of the Response.
    #     :param tool_outputs: The execution result of the tool. For detailed instructions, refer to the ToolOutput Object
    #     true: Fill in the context of the previous conversation and continue with streaming response.
    #     false: (Default) Non-streaming response, only reply with basic information of the conversation.
    #     :return:
    #     """
    #
    #     async for item in await self._submit_tool_outputs(
    #         conversation_id=conversation_id, chat_id=chat_id, stream=True, tool_outputs=tool_outputs
    #     ):
    #         yield item

    # @overload
    # async def _submit_tool_outputs(
    #     self, *, conversation_id: str, chat_id: str, stream: Literal[True], tool_outputs: List[ToolOutput]
    # ) -> AsyncStream[ChatEvent]: ...
    #
    # @overload
    # async def _submit_tool_outputs(
    #     self, *, conversation_id: str, chat_id: str, stream: Literal[False], tool_outputs: List[ToolOutput]
    # ) -> Chat: ...
    #
    # async def _submit_tool_outputs(
    #     self, *, conversation_id: str, chat_id: str, stream: Literal[True, False], tool_outputs: List[ToolOutput]
    # ) -> Union[Chat, AsyncStream[ChatEvent]]:
    #     url = f"{self._base_url}/v3/chat/submit_tool_outputs"
    #     params = {
    #         "conversation_id": conversation_id,
    #         "chat_id": chat_id,
    #     }
    #     body = {
    #         "tool_outputs": [i.model_dump() for i in tool_outputs],
    #         "stream": stream,
    #     }
    #
    #     if not stream:
    #         return await self._requester.arequest("post", url, False, Chat, params=params, body=body)
    #
    #     resp: AsyncIteratorHTTPResponse[str] = await self._requester.arequest(
    #         "post", url, True, None, params=params, body=body
    #     )
    #     return AsyncStream(
    #         resp.data, fields=["event", "data"], handler=_async_chat_stream_handler, raw_response=resp._raw_response
    #     )

    async def cancel(
        self,
        *,
        conversation_id: str,
        chat_id: str,
    ) -> Chat:
        """
        Call this API to cancel an ongoing chat.

        docs en: https://www.coze.com/docs/developer_guides/chat_cancel
        docs zh: https://www.coze.cn/docs/developer_guides/chat_cancel

        :param conversation_id: The Conversation ID can be viewed in the 'conversation_id' field of the Response when
        initiating a conversation through the Chat API.
        :param chat_id: The Chat ID can be viewed in the 'id' field of the Response when initiating a chat through the
        Chat API. If it is a streaming response, check the 'id' field in the chat event of the Response.
        :return:
        """
        url = f"{self._base_url}/v3/chat/cancel"
        body = {
            "conversation_id": conversation_id,
            "chat_id": chat_id,
        }
        return await self._requester.arequest("post", url, False, Chat, body=body)

    # @property
    # def messages(
    #     self,
    # ) -> "AsyncChatMessagesClient":
    #     if self._messages is None:
    #         from .message import AsyncChatMessagesClient
    #
    #         self._messages = AsyncChatMessagesClient(self._base_url, self._auth, self._requester)
    #     return self._messages
