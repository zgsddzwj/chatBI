import { useEffect, useState } from "react";
import type { ChartSpec, QueryResult } from "../types";

export interface Template {
  id: string;
  question: string;
  summary?: string;
  sql?: string | null;
  data?: QueryResult | null;
  chart?: ChartSpec | null;
  createdAt: string;
}

const STORAGE_KEY = "chatbi_templates";

export function useTemplates() {
  const [templates, setTemplates] = useState<Template[]>([]);

  useEffect(() => {
    const item = localStorage.getItem(STORAGE_KEY);
    if (item) {
      try {
        const parsed = JSON.parse(item) as Template[];
        setTemplates(parsed.filter(t => t.id && t.question));
      } catch {
        // ignore
      }
    }
  }, []);

  const saveTemplates = (list: Template[]) => {
    setTemplates(list);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
  };

  const addTemplate = (tpl: Omit<Template, "id" | "createdAt">) => {
    const newOne: Template = {
      ...tpl,
      id: Date.now().toString(36) + Math.random().toString(36).slice(2),
      createdAt: new Date().toISOString(),
    };
    const updated = [newOne, ...templates].slice(0, 100);
    saveTemplates(updated);
  };

  const removeTemplate = (id: string) => {
    const updated = templates.filter(t => t.id !== id);
    saveTemplates(updated);
  };

  return {
    templates,
    addTemplate,
    removeTemplate,
  };
}
