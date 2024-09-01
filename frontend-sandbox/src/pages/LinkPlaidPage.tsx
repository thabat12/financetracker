import axios from "axios";
import React, { useEffect } from "react";
import { useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { useState } from "react";


function LinkPlaidPage() {

    const authorizationToken = useSelector((state: any) => state.authorization);
    const navigate = useNavigate();

    const [institutionSelected, setInstitutionSelected] = useState<string | undefined>(undefined);
    const [institutionData, setInstitutionData] = useState<Array<any> | undefined>();

    async function getInstitutionData() {
        let data = await axios.get(`http://localhost:8000/institution_data?limit=10&data_type=transactions`);
        console.log("transaction institutions");
        console.log(data.data);
        const transactionInstitutions: Array<any> = data.data.institutions;  
        
        data = await axios.get("http://localhost:8000/institution_data?limit=10&data_type=investments");
        console.log("investments institutions");
        console.log(data.data);
        const investmentInstitutions: Array<any> = data.data.institutions;

        const institutionSet = new Set<string>();
        const iData: Array<any> = [];

        [...transactionInstitutions, ...investmentInstitutions].forEach(
            (elem) => {
                if (! institutionSet.has(elem.institution_id)) {
                    iData.push(elem);
                }
            }
        );
        sessionStorage.setItem("institutionData", JSON.stringify(iData));
        setInstitutionData(iData);
    }


    useEffect(
        () => {
            let cachedData = sessionStorage.getItem("institutionData");

            if (cachedData === undefined || cachedData === null) {
                getInstitutionData();
            } else {
                cachedData = sessionStorage.getItem("institutionData");
                if (cachedData !== null) {
                    const iData = JSON.parse(cachedData);
                    setInstitutionData(iData);
                }
            }
        }, []
    );


    const linkPlaidAccount = () => {
        if (institutionSelected === undefined) {
            alert("please select an institution under the dropdown!");
            return;
        }

        axios.post(`http://localhost:8000/plaid/link_account`, 
            {
                institution_id: 'ins_109508'
            }, 
            {
                headers: {
                    "Authorization": `Bearer ${authorizationToken}`,
                    "Content-Type": "application/json"
                }
            }).then(
            (response) => {
                console.log(response);
                if (response.data.message == 'success') {
                    navigate("/dashboard");
                }
            }
        );
    };

    let renderId = 0;


    return (
        <div>Link Plaid Page<br/>
            <button onClick={linkPlaidAccount}>Link Plaid Account {"<<<"}</button>
            <br/>
            <br/>
            
            <label><strong>Institution:</strong></label>
            <select
                id="exampleDropdown"
                value={institutionSelected}
                onChange={(e) => {setInstitutionSelected(e.target.id)}}
            >
                <option value="" disabled>Select an option</option>
                {
                    institutionData !== undefined ?
                    institutionData.map(
                        (elem) => {
                            return (
                                <option key={renderId++} id={elem.institution_id}>{elem.name}{
                                    elem.products.includes("transactions") ? `-(transactions)` : ""
                                } {
                                    elem.products.includes("investments") ? "-(investments)" : ""
                                }
                                </option>
                            )
                        }
                    ) : ""
                }
            </select>

            <br/>
            <label><strong>The authorization token from the app</strong></label>
            <br/>
            {authorizationToken}

        </div>
    );
}

export default LinkPlaidPage;