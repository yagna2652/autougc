"use client";

import { useState } from "react";
import { ThumbsUp, ThumbsDown, MessageSquare, X } from "lucide-react";

interface GenerationCardProps {
  traceId: string | null;
  onRate: (traceId: string, rating: number) => void;
  onAnnotate: (traceId: string, notes: string) => void;
}

export function GenerationCard({ traceId, onRate, onAnnotate }: GenerationCardProps) {
  const [rating, setRating] = useState<number | null>(null);
  const [showNotes, setShowNotes] = useState(false);
  const [notes, setNotes] = useState("");
  const [notesSaved, setNotesSaved] = useState(false);

  if (!traceId) return null;

  function handleRate(value: number) {
    const newRating = rating === value ? null : value;
    setRating(newRating);
    if (newRating !== null) {
      onRate(traceId!, newRating);
    }
  }

  function handleSaveNotes() {
    if (notes.trim()) {
      onAnnotate(traceId!, notes.trim());
      setNotesSaved(true);
      setTimeout(() => setNotesSaved(false), 2000);
    }
  }

  return (
    <div className="flex items-center gap-3 pt-2">
      <button
        type="button"
        onClick={() => handleRate(1)}
        className={`p-1.5 rounded-md transition-colors ${
          rating === 1
            ? "text-green-500 bg-green-500/10"
            : "text-muted-foreground hover:text-foreground hover:bg-secondary"
        }`}
        title="Good"
      >
        <ThumbsUp size={16} />
      </button>
      <button
        type="button"
        onClick={() => handleRate(-1)}
        className={`p-1.5 rounded-md transition-colors ${
          rating === -1
            ? "text-red-500 bg-red-500/10"
            : "text-muted-foreground hover:text-foreground hover:bg-secondary"
        }`}
        title="Bad"
      >
        <ThumbsDown size={16} />
      </button>

      <div className="h-4 w-px bg-border" />

      {showNotes ? (
        <div className="flex items-center gap-2 flex-1">
          <input
            type="text"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSaveNotes()}
            placeholder="Add a note..."
            className="input-field flex-1 !py-1 !text-xs"
            autoFocus
          />
          <button
            type="button"
            onClick={handleSaveNotes}
            className="text-xs px-2 py-1 rounded-md bg-primary text-primary-foreground"
          >
            {notesSaved ? "Saved" : "Save"}
          </button>
          <button
            type="button"
            onClick={() => setShowNotes(false)}
            className="p-1 text-muted-foreground hover:text-foreground"
          >
            <X size={14} />
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setShowNotes(true)}
          className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
          title="Add note"
        >
          <MessageSquare size={16} />
        </button>
      )}
    </div>
  );
}
