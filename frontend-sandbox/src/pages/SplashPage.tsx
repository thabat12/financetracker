import React, { useEffect } from "react";
import { CodeResponse, CredentialResponse, GoogleLogin, googleLogout, useGoogleLogin, UseGoogleLoginOptionsImplicitFlow } from "@react-oauth/google";
import { useState } from "react";
import axios, { AxiosResponse } from "axios";
// using someone else's component for react one tap login
import { useGoogleOneTapLogin } from "react-google-one-tap-login";
import { jwtDecode } from "jwt-decode";


const clientId = "797734322196-9i7q2teoas355etda5poi48mll0b3r2l.apps.googleusercontent.com";

function SplashPage() {

    type UserProfileType = {
        access_token? : string;
    }

    type UserDetailsType = {
        id? : string;
    }

    const [userProfile, setUserProfile] = useState<UserProfileType>({});
    const [userDetails, setUserDetails] = useState<UserDetailsType>({});

    const setUser = (codeResponse: UserProfileType) => {
        console.log(`with useGoogleLogin: ${JSON.stringify(codeResponse, null, 2)}`);
        setUserProfile(codeResponse);
    }

    const handleError = (error: Pick<CodeResponse, "error" | "error_description" | "error_uri">) => {
        console.log(error);
    }

    const login = useGoogleLogin({
        onSuccess: (codeResponse: UserProfileType) => setUser(codeResponse),
        onError: (error: Pick<CodeResponse, "error" | "error_description" | "error_uri">) => handleError(error)
    });

    const handleLogout = () => {
        googleLogout();
        setUserProfile({});
    }


    useEffect( () => {

            if (userProfile.access_token) {
                axios.get(`https://www.googleapis.com/oauth2/v1/userinfo?access_token=${userProfile.access_token}`,
                    {
                        headers: {
                            Authorization: `Bearer ${userProfile.access_token}`,
                            Accept: "application/json"
                        }
                    }
                )
                .then(
                    (res: AxiosResponse) => {
                        setUserDetails(res.data);

                    }
                ).catch(
                    (err) => {
                        console.log(err);
                    }
                )
            } else {
                const script = document.createElement("script");
                script.src = "https://accounts.google.com/gsi/client";
                script.async = true;
                script.onload = () => {
                    window.google.accounts.id.initialize({
                        client_id: clientId,
                        callback: (msg: any) => console.log(`with the onetaplogin ${JSON.stringify(msg, null, 2)}`)
                    })
                    window.google.accounts.id.prompt();
                }
                document.head.appendChild(script);
                setUserDetails({});
            }

            return () => {
            }
        }, [userProfile]
    );

    useEffect(() => {
        if (userDetails.id) {
            console.log("here is where I will go on and log in the user to my app");
            console.log(`the access token: ${userProfile.access_token}`);
            axios.post("http://localhost:8000/auth/login_google", 
            {
                access_token: userProfile.access_token
            },
            {
                headers: {'Content-Type': 'application/json'} 
            });
        }

    }, [userDetails])

    return (
        <div>
            <h1>Welcome to FinanceTracker-Sandbox!</h1>
            <div>
                    <div>

                        <label><strong>Using the useGoogleLogin component</strong></label>
                        <br/>
                        <button onClick={() => login()}>Log into google custom {"<<<"}</button>
                        <br/>
                        <button onClick={() => handleLogout()}>Log out user {">>>"}</button>
                        <br/>
                        <label><strong>Current user profile</strong></label>
                        <p>
                            {JSON.stringify(userDetails, null, 2)}
                        </p>
                    </div>

            </div>
        </div>
    )
}

export default SplashPage;