import React, { useEffect } from "react";
import { useSelector } from "react-redux";
import axios from "axios";
import { useState } from "react";

const SettingsPage = () => {

    const authorizationToken = useSelector((state: any) => state.authorization);
    const [accounts, setAccounts] = useState<Array<any> | undefined>(undefined);

    const getAccounts = async () => {
        const data = await axios.post("http://localhost:8000/data/get_accounts", null,
            {
                headers: {
                    "Authorization": `Bearer ${authorizationToken}`,
                    "Content-Type": "application/json"
                }
            }
        );

        console.log(data.data);

        sessionStorage.setItem("accounts", JSON.stringify(data.data.accounts));
        setAccounts(data.data.accounts);
    }

    useEffect(() => {

        const data = sessionStorage.getItem("accounts");

        if (data === undefined || data === null) {
            getAccounts();
        } else {
            const accountData = JSON.parse(data);
            if (data !== null || data !== undefined) {
                setAccounts(accountData);
            }
        }
    }, []);

    return (
        <div>
            this is the settings page
            <div>
                {
                    (accounts !== undefined) ? 
                    accounts.map(
                        (value, index) => {
                            return (
                                <div key={index} className="flex p-5">
                                    account_name: {value.account_name}<br/>
                                    account_type: {value.account_type}<br/>
                                    balance_available: {value.balance_available}<br/>
                                    balance_current: {value.balance_current}<br/>
                                    currency_code: {value.iso_currency_code}<br/>
                                    institution_id: {value.institution_id}<br/>
                                    update_status_date: {value.update_status_date}
                                </div>
                            )
                        }
                    ) : ""
                }
            </div>
        </div>
    );
}

export default SettingsPage;