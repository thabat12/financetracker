import { createSlice } from "@reduxjs/toolkit";
import { reduxAction } from "../constants";

const initialAuthorizationState: string = "";

const authorizationSlice = createSlice({
    name: 'authorization',
    initialState: initialAuthorizationState,
    reducers: {
        updateAuthorization(state, action) {
            return action.payload;
        }
    }
});

export const {updateAuthorization} = authorizationSlice.actions;
export default authorizationSlice.reducer;