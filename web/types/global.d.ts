// Global ambient type declarations for frontend scripts

interface LucideStatic {
    createIcons: () => void;
}

declare global {
    interface Window {
        lucide?: LucideStatic;
        toggleUnifiedNotifDropdown?: (e?: Event) => void;
        filterDropdownNotifs?: (cat: string, e?: Event) => void;
        quickMarkAllRead?: (e?: Event) => Promise<void>;
        quickMarkSingleRead?: (id: string, e?: Event) => Promise<void>;
    }
    const lucide: LucideStatic | undefined;
}

export {};
