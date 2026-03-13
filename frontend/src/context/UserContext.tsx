"use client";

import React, { createContext, useContext, useState, useEffect } from 'react';

interface UserContextType {
    userName: string;
    userRole: string;
    isDarkMode: boolean;
    updateUser: (name: string, role: string) => void;
    toggleDarkMode: () => void;
    setDarkMode: (dark: boolean) => void;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export function UserProvider({ children }: { children: React.ReactNode }) {
    const [userName, setUserName] = useState("Akash Raman");
    const [userRole, setUserRole] = useState("Senior Analyst");
    const [isDarkMode, setIsDarkMode] = useState(true);

    useEffect(() => {
        const savedName = localStorage.getItem('ncel_user_name');
        const savedRole = localStorage.getItem('ncel_user_role');
        const savedTheme = localStorage.getItem('ncel_dark_mode');
        
        if (savedName) setUserName(savedName);
        if (savedRole) setUserRole(savedRole);
        if (savedTheme !== null) setIsDarkMode(savedTheme === 'true');
    }, []);

    const updateUser = (name: string, role: string) => {
        setUserName(name);
        setUserRole(role);
        localStorage.setItem('ncel_user_name', name);
        localStorage.setItem('ncel_user_role', role);
    };

    const toggleDarkMode = () => {
        setIsDarkMode(prev => {
            const newValue = !prev;
            localStorage.setItem('ncel_dark_mode', String(newValue));
            return newValue;
        });
    };

    const setDarkMode = (dark: boolean) => {
        setIsDarkMode(dark);
        localStorage.setItem('ncel_dark_mode', String(dark));
    };

    return (
        <UserContext.Provider value={{ userName, userRole, isDarkMode, updateUser, toggleDarkMode, setDarkMode }}>
            {children}
        </UserContext.Provider>
    );
}

export function useUser() {
    const context = useContext(UserContext);
    if (context === undefined) {
        throw new Error('useUser must be used within a UserProvider');
    }
    return context;
}
