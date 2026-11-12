import { Fragment, type ReactNode } from "react";

// Small presentation subset. React escapes every string; no HTML, active links,
// images, scripts or remote fetching. Unrecognized markup remains plain text.
function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*\n]+\*\*|`[^`\n]+`|!?\[[^\]\n]*\]\([^\)\n]*\))/g).map((part,index)=>{
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={index}>{part.slice(2,-2)}</strong>;
    if (part.startsWith("`") && part.endsWith("`")) return <code key={index}>{part.slice(1,-1)}</code>;
    const link=part.match(/^(!?)\[([^\]]*)\]\(([^)]*)\)$/);
    if (link) return <Fragment key={index}>{link[2]}{link[1] ? " (image omitted)" : " ("+link[3]+")"}</Fragment>;
    return part;
  });
}

export default function ConversationMessage({content}:{content:string}) {
  const lines=content.split("\n"), blocks:ReactNode[]=[];
  for (let i=0;i<lines.length;) {
    if (!lines[i].trim()) {i++;continue;}
    if (/^```/.test(lines[i])) {
      const code:string[]=[];i++;
      while(i<lines.length && !/^```/.test(lines[i])) code.push(lines[i++]);
      if(i<lines.length)i++;
      blocks.push(<pre key={blocks.length}><code>{code.join("\n")}</code></pre>);continue;
    }
    const list=lines[i].match(/^\s*(?:([-*])|\d+\.)\s+(.+)$/);
    if(list) {
      const ordered=!list[1],items:ReactNode[]=[];
      while(i<lines.length) {
        const match=lines[i].match(/^\s*(?:([-*])|\d+\.)\s+(.+)$/);
        if(!match || (!match[1])!==ordered)break;
        items.push(<li key={items.length}>{inline(match[2])}</li>);i++;
      }
      blocks.push(ordered?<ol key={blocks.length}>{items}</ol>:<ul key={blocks.length}>{items}</ul>);continue;
    }
    blocks.push(<p key={blocks.length}>{inline(lines[i++].replace(/^#{1,3}\s+/,""))}</p>);
  }
  return <div className="ai-message-content">{blocks}</div>;
}
