/**
 * Local vault mirror writer.
 *
 * Writes captured notes as Markdown files into a local vault folder on
 * the device. On Android the app's external documents directory is used
 * so the files can be shared with an Obsidian sync folder (e.g. via
 * Syncthing or a mounted NAS share) when available.
 *
 * The file layout mirrors what the desktop vault watcher expects:
 *   <captureFolder>/<YYYY-MM-DD> <template> <slug>.md
 * with YAML frontmatter (title, tags, created, source: mobile).
 */
import { FileSystem } from "expo-file-system";
import { AppSettings, CapturedNote } from "../src/types";

function vaultRoot(settings: AppSettings): string {
  // Android: shared Documents dir so file managers / sync tools see it.
  const base = FileSystem.documentDirectory ?? "";
  return `${base}obsidian-vault/${settings.captureFolder}`;
}

function slugify(text: string): string {
  return (
    text
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 60) || "note"
  );
}

function frontmatter(note: CapturedNote): string {
  const created = new Date(note.createdAt).toISOString();
  const tags = note.tags.length
    ? note.tags.map((t) => `  - ${t}`).join("\n")
    : "  - mobile";
  return [
    "---",
    `title: "${note.title.replace(/"/g, '\\"')}"`,
    "tags:",
    tags,
    `created: ${created}`,
    "source: mobile",
    `template: ${note.template}`,
    "---",
    "",
  ].join("\n");
}

/**
 * Write a captured note to the local vault mirror.
 *
 * Returns the relative vault path (e.g. "Inbox/2026-11-19 idea-foo.md").
 */
export async function writeNoteToVault(
  settings: AppSettings,
  note: CapturedNote
): Promise<string> {
  const root = vaultRoot(settings);
  if (!(await FileSystem.getInfoAsync(root)).exists) {
    await FileSystem.makeDirectoryAsync(root, { intermediates: true });
  }

  const date = new Date(note.createdAt).toISOString().slice(0, 10);
  const filename = `${date} ${note.template}-${slugify(note.title)}.md`;
  const filePath = `${root}/${filename}`;

  const content = `${frontmatter(note)}# ${note.title}\n\n${note.body}\n`;
  await FileSystem.writeAsStringAsync(filePath, content, { encoding: "utf8" });

  return `${settings.captureFolder}/${filename}`;
}
