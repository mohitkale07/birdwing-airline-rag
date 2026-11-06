import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import type { ChatStreamEvent } from "../schemas/api";

interface ChatState {
  events: Array<{ requestId: string; event: ChatStreamEvent }>;
}

const initialState: ChatState = { events: [] };

const chatSlice = createSlice({
  name: "chat",
  initialState,
  reducers: {
    chatStreamEventReceived: (
      state,
      action: PayloadAction<{ requestId: string; event: ChatStreamEvent }>,
    ) => {
      state.events.push(action.payload);
    },
    clearChatStreamEvents: (state) => {
      state.events = [];
    },
  },
});

export const { chatStreamEventReceived, clearChatStreamEvents } =
  chatSlice.actions;
export default chatSlice.reducer;
