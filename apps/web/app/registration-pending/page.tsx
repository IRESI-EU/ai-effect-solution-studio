import Link from "next/link";
import { Clock3 } from "lucide-react";

export default function RegistrationPendingPage() {
  return <main className="auth-page auth-page-centered"><section className="auth-form-card pending-card"><div className="auth-form-icon"><Clock3 size={26} /></div><span className="auth-eyebrow">Request received</span><h1>Administrator approval is pending</h1><p>Your account cannot sign in until a platform administrator verifies the email, requested role and node affiliation. Please contact the AI-EFFECT administrator if the request is urgent.</p><Link className="auth-primary-link" href="/login">Return to sign in</Link><Link className="auth-public-link" href="/catalogue">Browse the public catalogue</Link></section></main>;
}
