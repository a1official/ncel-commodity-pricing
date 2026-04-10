import type { Metadata } from "next";
import { Inter, Outfit } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import TopBar from "@/components/TopBar";
import { UserProvider } from "@/context/UserContext";
import { CommodityProvider } from "@/context/CommodityContext";
import ChatbotWidget from "@/components/ChatbotWidget";
import PerformanceMonitor from "@/components/PerformanceMonitor";
import QueryProvider from "@/components/providers/QueryProvider";

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
        <html lang="en">
            <body className={`${inter.variable} ${outfit.variable} font-body app-shell overflow-hidden`}>
                <UserProvider>
                    <QueryProvider>
                        <CommodityProvider>
                            <PerformanceMonitor />
                            <div className="flex h-screen w-screen bg-[var(--app-bg)] text-[var(--app-fg)] transition-colors duration-300">
                                <Sidebar />
                                <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
                                    <TopBar />
                                    <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-8 xl:px-10 scroll-smooth">
                                        {children}
                                    </main>
                                </div>
                            </div>
                            <ChatbotWidget />
                        </CommodityProvider>
                    </QueryProvider>
                </UserProvider>
            </body>
        </html>
    );
}
