import axios from "axios";
import React from "react";
import { useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";

function LinkPlaidPage() {

    const authorizationToken = useSelector((state: any) => state.authorization);
    const navigate = useNavigate();

    const linkPlaidAccount = () => {
        axios.post(`http://localhost:8000/plaid/link_account`, null, {
            headers: {
                "Authorization": `Bearer ${authorizationToken}`,
                "Content-Type": "application/json"
            }
        }).then(
            (response) => {
                console.log(response);
                navigate("/dashboard");
            }
        )
    };


    return (
        <div>Link Plaid Page<br/>
            <button onClick={linkPlaidAccount}>Link Plaid Account {"<<<"}</button>
            <br/>
            <label><strong>The authorization token from the app</strong></label>
            <br/>
            {authorizationToken}

        </div>
    );
}

export default LinkPlaidPage;