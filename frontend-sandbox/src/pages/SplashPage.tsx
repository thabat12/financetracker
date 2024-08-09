import React, { useEffect } from "react";
import { CodeResponse, CredentialResponse, GoogleLogin, googleLogout, useGoogleLogin, UseGoogleLoginOptionsImplicitFlow } from "@react-oauth/google";
import { useState } from "react";
import axios, { AxiosResponse } from "axios";
// using someone else's component for react one tap login
import { useGoogleOneTapLogin } from "react-google-one-tap-login";
import { jwtDecode } from "jwt-decode";


const clientId = "797734322196-9i7q2teoas355etda5poi48mll0b3r2l.apps.googleusercontent.com";

function SplashPage() {
    type UserProfile = {
        access_token? : string;
    }

    type GoogleUserProfile = {
        credential? : string;
    }

    const [userProfile, setUserProfile] = useState<UserProfile>({});
    const [userDetails, setUserDetails] = useState({});

    const setUser = (codeResponse: UserProfile) => {
        console.log(codeResponse);
        setUserProfile(codeResponse);
    }

    const handleError = (error: Pick<CodeResponse, "error" | "error_description" | "error_uri">) => {
        console.log(error);
    }

    const login = useGoogleLogin({
        onSuccess: (codeResponse: UserProfile) => setUser(codeResponse),
        onError: (error: Pick<CodeResponse, "error" | "error_description" | "error_uri">) => handleError(error)
    });

    const handleLogout = () => {
        googleLogout();
        setUserProfile({});
    }

    async function retrieveJWT(data: any) {
    }

    async function verifyToken(idToken: any) {
    }

    const loginGoogle = (response: GoogleUserProfile) => {
        const token = response.credential;
    }


    useEffect( () => {

            const script = document.createElement("script");
            script.src = "https://accounts.google.com/gsi/client";
            script.async = true;
            script.onload = () => {
                window.google.accounts.id.initialize({
                    client_id: clientId,
                    callback: (msg: any) => retrieveJWT(msg)
                })
                window.google.accounts.id.prompt();
            }
            document.head.appendChild(script);


            console.log(JSON.stringify(userProfile, null, 2));
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
                setUserDetails({});
            }

            return () => {
                document.head.removeChild(script);
            }
        }, [userProfile]
    )

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