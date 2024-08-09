import { createSlice } from "@reduxjs/toolkit";
import { reduxAction } from "../constants";

const initialTransactionsState: Array<object> = [];

const transactionsSlice = createSlice({
    name: 'transactions',
    initialState: initialTransactionsState,
    reducers: {
        updateTransactions(state, action) {
            return action.payload;
        }
    }
});

export const {updateTransactions} = transactionsSlice.actions;
export default transactionsSlice.reducer;