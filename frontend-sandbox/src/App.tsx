import React from 'react';
import logo from './logo.svg';
import './App.css';

import {Routes, Route, BrowserRouter, Link} from 'react-router-dom'
import SplashPage from './pages/SplashPage';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import AccountPage from './pages/AccountPage';


function App() {
  return (
    <BrowserRouter>
        <Routes>
            <Route path="/" element={<SplashPage/>}/>
            <Route path="/login" element={<LoginPage/>}/>
            <Route path="/dashboard" element={<DashboardPage/>}/>
            <Route path="/account" element={<AccountPage/>}/>
        </Routes>
    </BrowserRouter>
  );
}

export default App;
