"use client";

import React, { createContext, useContext, useState, useEffect } from 'react';

interface UserContextType {
    userName: string;
    userRole: string;
    updateUser: (name: string, role: string) => void;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export function UserProvider({ children }: { children: React.ReactNode }) {
    const [userName, setUserName] = useState("Akash Raman");
    const [userRole, setUserRole] = useState("Senior Analyst");

    // Load from localStorage on mount
    useEffect(() => {
        const savedName = localStorage.getItem('ncel_user_name');
        const savedRole = localStorage.getItem('ncel_user_role');
        if (savedName) setUserName(savedName);
        if (savedRole) setUserRole(savedRole);
    }, []);

    const updateUser = (name: string, role: string) => {
        setUserName(name);
        setUserRole(role);
        localStorage.setItem('ncel_user_name', name);
        localStorage.setItem('ncel_user_role', role);
    };

    return (
        <UserContext.Provider value={{ userName, userRole, updateUser }}>
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
