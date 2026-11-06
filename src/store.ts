import { configureStore } from "@reduxjs/toolkit";
import authReducer from "./features/authSlice";
import chatReducer from "./features/chatSlice";
import { api } from "./services/api";

export const store = configureStore({
  reducer: {
    auth: authReducer,
    chat: chatReducer,
    [api.reducerPath]: api.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(api.middleware),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
