import React from 'react';
import logo from './logo.svg';
import './App.css';

import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import SplashPage from './pages/SplashPage';
import LoginPage from './pages/LinkPlaidPage';
import DashboardPage from './pages/DashboardPage';
import AccountPage from './pages/AccountPage';
import { GoogleOAuthProvider } from '@react-oauth/google';
import SummaryPage from './pages/SummaryPage';
import TransactionsPage from './pages/TransactionsPage';
import SettingsPage from './pages/SettingsPage';
import LinkPlaidPage from './pages/LinkPlaidPage';

const clientId = "797734322196-9i7q2teoas355etda5poi48mll0b3r2l.apps.googleusercontent.com";

function App() {
  return (
    <GoogleOAuthProvider clientId={clientId}>
        <Router>
            <Routes>
                <Route path="/" element={<SplashPage/>}/>
                <Route path="/link_plaid" element={<LinkPlaidPage/>}/>
                <Route path="/dashboard" element={<DashboardPage/>}>
                    <Route path="summary" element={<SummaryPage/>}/>
                    <Route path="transactions" element={<TransactionsPage/>}/>
                    <Route path="settings" element={<SettingsPage/>}/>
                </Route>
            </Routes>
        </Router>
    </GoogleOAuthProvider>
  );
}

export default App;
