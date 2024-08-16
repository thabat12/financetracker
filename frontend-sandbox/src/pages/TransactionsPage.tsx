import axios from "axios";
import React, { useEffect } from "react";
import { useSelector } from "react-redux";
import { useState } from "react";

const TransactionsPage = () => {

    const authorizationToken = useSelector((state: any) => state.authorization);
    console.log(`the authorization token under transactions page: ${authorizationToken}`)
    const [transactions, setTransactions] = useState<Array<any>>([]);

    useEffect(() => {
        axios.post(`http://localhost:8000/data/get_transactions`, null,
            {
                headers: {
                    "Authorization": `Bearer ${authorizationToken}`,
                    "Content-Type": "application/json"
                }
            }
        ).then(
            (response) => {
                setTransactions([{name: "transaction1", amount: "3"}, {name: "transaction2", amount: "2"}]);

                console.log(response);
            }
        )
    }, []);


    return (
        <div>
            this is the transactions page
            <button onClick={() => {setTransactions([{name: "transaction1", amount: "3"}, {name: "transaction2", amount: "2"}]);}}>Set transactions</button>
            {transactions.map((value, index) => {
                return (
                    <div key={String(index)}>
                        {JSON.stringify(value, null, 2)}
                    </div>
                )
            })}
        </div>
    )
}

export default TransactionsPage;