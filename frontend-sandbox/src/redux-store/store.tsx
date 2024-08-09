import { configureStore } from "@reduxjs/toolkit";
import transactionsReducer from "./slices/transactionsSlice";

const rootStore = configureStore({
    reducer: {
        transactions: transactionsReducer
    }
});

export default rootStore;