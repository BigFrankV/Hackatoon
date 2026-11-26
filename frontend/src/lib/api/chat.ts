import { apiRequest } from "@/lib/api/client";

export interface ChatCitation {
  order: number;
  document_id: string;
  document_title: string;
  location: string | null;
  page_number: number | null;
  excerpt: string;
  similarity: number;
}

export interface ChatResponse {
  conversation_id: string;
  user_message_id: string;
  assistant_message_id: string;
  answer: string;
  model: string;
  grounded: boolean;
  notice: string | null;
  citations: ChatCitation[];
}

export function sendChatMessage(content: string, conversationId?: string) {
  return apiRequest<ChatResponse>("/chat/messages", {
    method: "POST",
    body: JSON.stringify({
      content,
      conversation_id: conversationId || null,
    }),
  });
}
