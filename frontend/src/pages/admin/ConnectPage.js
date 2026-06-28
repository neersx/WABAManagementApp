import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Plug, ArrowRight, CheckCircle2, Loader2 } from "lucide-react";
import { Link } from "react-router-dom";

export default function ConnectPage() {
    const [launching, setLaunching] = useState(false);
    const [recent, setRecent] = useState([]);

    const refresh = async () => {
        try {
            const r = await api.get("/wabas");
            setRecent(r.data);
        } catch {}
    };
    useEffect(() => {
        refresh();
    }, []);

    const launchSignup = async () => {
        setLaunching(true);
        try {
            // Mock: generate a fake auth code as if returned by Meta JS SDK
            const code = `AUTHCODE_${Math.random().toString(36).slice(2, 10)}`;
            const r = await api.post("/onboarding/exchange", { code });
            toast.success(
                `Connected WABA ${r.data.waba.waba_id} · phone ${r.data.phone_number.display_phone_number}`,
            );
            await refresh();
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Onboarding failed");
        } finally {
            setLaunching(false);
        }
    };

    return (
        <AppShell>
            <PageHeader
                breadcrumb={<span>Admin / Connect WhatsApp</span>}
                title="Connect WhatsApp"
                description="Run the (mock) Meta Embedded Signup flow to attach a WhatsApp Business Account."
            />
            <div className="grid gap-6 lg:grid-cols-2">
                <div className="rounded-xl border bg-card p-6">
                    <div className="flex items-start gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                            <Plug className="h-5 w-5" />
                        </div>
                        <div>
                            <div className="text-base font-semibold">Embedded Signup</div>
                            <p className="mt-1 text-sm text-muted-foreground">
                                In production, this launches Meta&apos;s official Embedded Signup
                                dialog. In mock mode it returns a synthetic auth code which we
                                exchange server-side for a long-lived business token.
                            </p>
                        </div>
                    </div>
                    <div className="mt-6">
                        <Button onClick={launchSignup} disabled={launching} data-testid="connect-launch-signup">
                            {launching ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Exchanging...
                                </>
                            ) : (
                                <>
                                    Launch Embedded Signup <ArrowRight className="ml-2 h-4 w-4" />
                                </>
                            )}
                        </Button>
                    </div>
                    <div className="mt-6 rounded-lg border bg-secondary/40 p-3 text-xs text-muted-foreground">
                        Tokens are encrypted at rest with Fernet and never returned to the
                        frontend. The server subscribes the app to the WABA&apos;s webhooks and
                        registers the phone number on your behalf.
                    </div>
                </div>
                <div className="rounded-xl border bg-card p-6">
                    <div className="text-base font-semibold">Recently connected</div>
                    {recent.length === 0 ? (
                        <p className="mt-3 text-sm text-muted-foreground">
                            No WABAs yet. Use the button to create your first one in mock mode.
                        </p>
                    ) : (
                        <ul className="mt-4 space-y-3 text-sm" data-testid="connect-recent-list">
                            {recent.slice(0, 5).map((w) => (
                                <li
                                    key={w.waba_id}
                                    className="flex items-center justify-between rounded-lg border bg-background p-3"
                                >
                                    <div>
                                        <div className="flex items-center gap-2 font-medium">
                                            <CheckCircle2 className="h-4 w-4 text-[hsl(152_55%_35%)]" />
                                            {w.name}
                                        </div>
                                        <div className="text-xs text-muted-foreground">{w.waba_id}</div>
                                    </div>
                                    <Link to="/app/wabas" className="text-xs font-medium text-primary">
                                        View →
                                    </Link>
                                </li>
                            ))}
                        </ul>
                    )}
                </div>
            </div>
        </AppShell>
    );
}
