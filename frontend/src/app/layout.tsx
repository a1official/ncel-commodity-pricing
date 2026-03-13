import type { Metadata } from "next";
import { Inter, Outfit } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import TopBar from "@/components/TopBar";
import { UserProvider } from "@/context/UserContext";
import ClientOnly from "@/components/ClientOnly";
import ChatbotWidget from "@/components/ChatbotWidget";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const outfit = Outfit({ subsets: ["latin"], variable: "--font-outfit" });

export const metadata: Metadata = {
    title: "NCEL | Commodity Market Intelligence",
    description: "Enterprise-grade price intelligence platform for Indian agricultural & marine commodities.",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en" className="dark">
            <body className={`${inter.variable} ${outfit.variable} font-body bg-slate-950 text-slate-200 overflow-hidden`}>
                <UserProvider>
                    <div className="flex h-screen w-screen bg-slate-50 dark:bg-slate-950">
                        <Sidebar />
                        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
                            <TopBar />
                            <main className="flex-1 overflow-y-auto px-10 py-8 scroll-smooth">
                                {children}
                            </main>
                        </div>
                    </div>
                    <ChatbotWidget />
                </UserProvider>
            </body>
        </html>
    );
}
