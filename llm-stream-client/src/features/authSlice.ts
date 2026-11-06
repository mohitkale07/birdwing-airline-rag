import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import type { AuthUser } from "../schemas/api";

interface AuthState {
  user: AuthUser | null;
}

const initialState: AuthState = {
  user: null,
};

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    setCurrentUser: (state, action: PayloadAction<AuthUser>) => {
      state.user = action.payload;
    },
    clearCredentials: (state) => {
      state.user = null;
    },
  },
});

export const { setCurrentUser, clearCredentials } = authSlice.actions;
export default authSlice.reducer;
