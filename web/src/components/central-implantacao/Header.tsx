"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { smStages } from "@/data/sm-process";
import { leStages } from "@/data/le-process";
import { modules } from "@/data/modules";
import { templates } from "@/data/templates";

type SearchItem = { label: string; group: string; href: string };

const searchIndex: SearchItem[] = [
  ...smStages.map((stage) => ({ label: stage.title, group: "Etapa · Small & Medium", href: `/processos/sm/${stage.id}` })),
  ...leStages.map((stage) => ({ label: stage.title, group: "Etapa · Large Enterprise", href: `/processos/le/${stage.id}` })),
  ...modules.map((mod) => ({ label: mod.title, group: "Módulo", href: `/processos/modulos/${mod.id}` })),
  ...templates.map((tpl) => ({ label: tpl.title, group: "Template de e-mail", href: "/processos/templates" })),
];

const norm = (value: string) => value.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

export default function Header() {
  const [query, setQuery] = useState("");
  const results = useMemo(() => {
    const q = norm(query.trim());
    if (!q) return [];
    return searchIndex.filter((item) => norm(item.label).includes(q)).slice(0, 8);
  }, [query]);

  return (
    <header className="ci-header">
      <div className="ci-search">
        <input
          placeholder="O que você precisa fazer? Ex.: como solicitar cargas, termo de homologação, integração..."
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onBlur={() => setTimeout(() => setQuery(""), 150)}
        />
        {results.length > 0 && (
          <div className="ci-search-results">
            {results.map((item, index) => (
              <Link key={`${item.href}-${index}`} href={item.href}>
                {item.label}
                <small>{item.group}</small>
              </Link>
            ))}
          </div>
        )}
      </div>
      <div className="ci-avatar" title="Minha conta" aria-label="Minha conta" />
    </header>
  );
}
