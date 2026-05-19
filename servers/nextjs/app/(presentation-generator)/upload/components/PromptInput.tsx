import { Textarea } from "@/components/ui/textarea";
import { PencilIcon } from "lucide-react";

interface PromptInputProps {
  value: string;
  onChange: (value: string) => void;
}

const EXAMPLE_PROMPTS = [
  "Company Q3 performance review",
  "Introduction to machine learning",
  "Marketing strategy for a new product",
  "Climate change: causes and solutions",
];

export function PromptInput({ value, onChange }: PromptInputProps) {
  return (
    <div className="relative font-syne border border-[#DBDBDB99] rounded-[8px] px-[10px] py-3"
      style={{ boxShadow: "0 4px 14px 0 rgba(0, 0, 0, 0.04)" }}
    >
      <div className="flex items-center gap-2 mb-1">
        <PencilIcon className="w-3.5 h-3.5" />
        <p className="text-sm font-normal text-[#333333] font-syne">Write prompt</p>
      </div>
      <Textarea
        value={value}
        autoFocus={true}
        rows={4}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Start with your idea… we’ll handle the slides"
        data-testid="prompt-input"
        className="px-2 py-0 font-medium shadow-none font-syne indent-4 text-base min-h-[120px] max-h-[250px] focus-visible:ring-offset-0 focus-visible:ring-transparent focus-visible:ring-0 border-none overflow-y-auto custom_scrollbar"
      />
      {!value && (
        <div className="flex flex-wrap gap-2 mt-2 pt-2 border-t border-[#DBDBDB44]">
          {EXAMPLE_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => onChange(prompt)}
              className="text-xs font-medium text-[#5146E5] bg-[#F0EFFE] hover:bg-[#E4E1FD] rounded-full px-3 py-1 transition-colors"
            >
              {prompt}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}