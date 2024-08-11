import { combineReducers, configureStore } from "@reduxjs/toolkit";
import transactionsReducer from "./slices/transactionsSlice";
import authorizationReducer from "./slices/authorizationSlice";

import { persistStore, persistReducer } from "redux-persist";
import storage from "redux-persist/lib/storage";

const persistConfig = {
    key: "root",
    storage,
    whitelist: ["authorization"]
};

const rootReducer = combineReducers({
    transactions: transactionsReducer,
    authorization: authorizationReducer
});

const persistedRootReducer = persistReducer(persistConfig, rootReducer);

const rootStore = configureStore({
    reducer: persistedRootReducer
});

const rootPersistor = persistStore(rootStore);

export default rootStore;
export {rootPersistor};