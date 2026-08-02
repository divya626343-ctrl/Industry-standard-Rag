import { useState, type KeyboardEvent } from "react";
import { SendButtonIcon } from "./icons/icons";

interface Props {
  disabled: boolean;
  disabledReason?: string;
  onSend: (query: string) => void;
}

export function QueryInput({ disabled, disabledReason, onSend }: Props) {
  const [value, setValue] = useState("");

  const submit = () => {
    if (!value.trim() || disabled) return;
    onSend(value.trim());
    setValue("");
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") submit();
  };

  return (
    <div className="query-input-wrap">
      <input
        type="text"
        placeholder={disabled && disabledReason ? disabledReason : "Enter your query"}
        value={value}
        disabled={disabled}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={onKeyDown}
      />
      <button className="send-btn" onClick={submit} disabled={disabled || !value.trim()} aria-label="Send">
        <SendButtonIcon size={24} />
      </button>
    </div>
  );
}
