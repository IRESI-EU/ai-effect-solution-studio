import Link from "next/link";

async function getSolutions() {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/solutions`, {
    cache: "no-store",
  });

  if (!res.ok) {
    return [];
  }

  return res.json();
}

export default async function SolutionsPage() {
  const solutions = await getSolutions();

  return (
    <div className="page">
      <span className="badge">AI Vendor Workspace</span>
      <h1>Saved solutions</h1>
      <p>
        Reopen saved workflow designs, edit them in the Builder, validate them,
        and submit them to the WP3 orchestrator.
      </p>

      <div style={{ display: "grid", gap: 16, marginTop: 24 }}>
        {solutions.length === 0 && (
          <section className="card" style={{ padding: 24 }}>
            <h2>No saved solutions yet</h2>
            <p>Create one from the Builder using Save draft.</p>
            <Link href="/builder" className="button">
              Open Builder
            </Link>
          </section>
        )}

        {solutions.map((solution: any) => (
          <section key={solution.id} className="card" style={{ padding: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <div>
                <span className="badge">{solution.status}</span>
                <h2>{solution.name}</h2>
                <p>{solution.description || "No description provided."}</p>
                <p style={{ color: "#667085" }}>
                  Nodes: {solution.nodes?.length || 0} | Edges:{" "}
                  {solution.edges?.length || 0}
                </p>
              </div>

              <Link
                href={`/builder?solutionId=${solution.id}`}
                style={{
                  alignSelf: "center",
                  background: "#075985",
                  color: "white",
                  padding: "12px 18px",
                  borderRadius: 10,
                  fontWeight: 800,
                  textDecoration: "none",
                }}
              >
                Open in Builder
              </Link>
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}