import axios from "axios";
import type {
  ChatAnswer,
  Conversation,
  ConversationDetail,
} from "./types";

const api = axios.create({
  baseURL: "/",
  timeout: 90000,
});

export interface ChatPayload {
  question: string;
  conversation_id?: number | null;
  history?: { role: "user" | "assistant"; content: string }[];
}

export const sendChat = async (payload: ChatPayload): Promise<ChatAnswer> => {
  const { data } = await api.post<ChatAnswer>("/api/chat", payload);
  return data;
};

export const listConversations = async (): Promise<Conversation[]> => {
  const { data } = await api.get<Conversation[]>("/api/conversations");
  return data;
};

export const getConversation = async (
  id: number,
): Promise<ConversationDetail> => {
  const { data } = await api.get<ConversationDetail>(`/api/conversations/${id}`);
  return data;
};

export const deleteConversation = async (id: number): Promise<void> => {
  await api.delete(`/api/conversations/${id}`);
};

export const getSamples = async (): Promise<string[]> => {
  const { data } = await api.get<{ questions: string[] }>("/api/meta/samples");
  return data.questions;
};
