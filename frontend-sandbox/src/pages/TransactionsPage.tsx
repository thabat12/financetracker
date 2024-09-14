import axios from "axios";
import React, { useEffect } from "react";
import { useSelector } from "react-redux";
import { useState } from "react";

const TransactionsPage = () => {

    const authorizationToken = useSelector((state: any) => state.authorization);
    console.log(`the authorization token under transactions page: ${authorizationToken}`)
    const [transactions, setTransactions] = useState<Array<any>>([]);

    const getTransactions = async () => {
        const data = await axios.post(`http://localhost:8000/data/get_transactions`, null,
            {
                headers: {
                    "Authorization": `Bearer ${authorizationToken}`,
                    "Content-Type": "application/json"
                }
            }
        );

        const transactionData = data.data.transactions;
        sessionStorage.setItem("transactions", JSON.stringify(transactionData));
        setTransactions(transactionData);
    }

    useEffect(() => {
        const data = sessionStorage.getItem("transactions");
        if (data === null || data === undefined) {
            getTransactions();
        } else {
            const transactionData = sessionStorage.getItem("transactions");

            if (data !== null) {
                const transactions = JSON.parse(data);
                setTransactions(transactions);
            }
        }
    }, []);

    return (
        <div>
            this is the transactions page
            <br/>
            <button 
                onClick={() => {sessionStorage.removeItem("transactions");}}
                className="flex font-bold p-2 bg-gray-100">Refresh</button>
            {transactions.map((value, index) => {
                return (
                    <div key={String(index)} className="flex p-5 background">
                        name: {value.name}<br/>
                        amount: {value.amount}<br/>
                        category: {value.personal_finance_category}<br/>
                        date: {value.authorized_date}<br/>
                        merchant_id: {value.merchant_id}<br/>
                        institution_id: {value.institution_id}
                    </div>
                )
            })}
        </div>
    )
}

export default TransactionsPage;