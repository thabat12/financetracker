import React from 'react';
import logo from './logo.svg';
import './App.css';

import {Routes, Route, BrowserRouter, Link} from 'react-router-dom'
import SplashPage from './pages/SplashPage';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import AccountPage from './pages/AccountPage';
import { GoogleOAuthProvider } from '@react-oauth/google';


const clientId = "797734322196-9i7q2teoas355etda5poi48mll0b3r2l.apps.googleusercontent.com";

function App() {
  return (
    <GoogleOAuthProvider clientId={clientId}>
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<SplashPage/>}/>
                <Route path="/login" element={<LoginPage/>}/>
                <Route path="/dashboard" element={<DashboardPage/>}/>
                <Route path="/account" element={<AccountPage/>}/>
            </Routes>
        </BrowserRouter>
    </GoogleOAuthProvider>
  );
}

export default App;
