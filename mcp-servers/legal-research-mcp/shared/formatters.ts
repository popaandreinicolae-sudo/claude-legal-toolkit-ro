import { CHARACTER_LIMIT } from "./constants.js";

export function truncateText(text: string, limit: number = CHARACTER_LIMIT): { text: string; truncated: boolean; totalChars: number } {
  const totalChars = text.length;
  if (totalChars <= limit) return { text, truncated: false, totalChars };
  const keepStart = Math.floor(limit * 0.75);
  const keepEnd = limit - keepStart - 50;
  const truncated = text.slice(0, keepStart) + "\n\n[...TRUNCAT — " + totalChars + " caractere total...]\n\n" + text.slice(-keepEnd);
  return { text: truncated, truncated: true, totalChars };
}

export function formatCelexCitation(celex: string, title: string, date: string): string {
  return `**${title}**\nCELEX: ${celex} | Data: ${date}\nURL: https://eur-lex.europa.eu/legal-content/RO/TXT/?uri=CELEX:${celex}`;
}

export function formatEchrCitation(caseName: string, appNo: string, date: string, ecli: string): string {
  return `**${caseName}** (cererea nr. ${appNo})\nData: ${date} | ECLI: ${ecli}\nURL: https://hudoc.echr.coe.int/eng?i=${ecli}`;
}

export function formatZoteroCitation(title: string, creators: string[], date: string): string {
  const authors = creators.length > 0 ? creators.join(", ") : "Autor necunoscut";
  return `${authors}, *${title}*, ${date}`;
}
