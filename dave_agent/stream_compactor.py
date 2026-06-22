class StreamCompactor:
    @staticmethod
    def compact(chunks, model=None):
        compacted = {
            "object": "chat.completion.stream",
            "chunk_count": len(chunks),
            "choices": [],
            "events": [],
        }
        choices = {}
        reasoning_keys = {"reasoning"}
        if model and "deepseek" in model.lower():
            reasoning_keys.add("reasoning_content")

        def set_or_event(target, key, value, chunk_index):
            if key not in target:
                target[key] = value
            elif target[key] is None and value is not None:
                target[key] = value
            elif target[key] != value:
                target.setdefault("events", []).append({"chunk": chunk_index, key: value})

        for chunk_index, chunk in enumerate(chunks):
            for key, value in chunk.items():
                if key == "choices":
                    continue
                if key == "object":
                    set_or_event(compacted, "chunk_object", value, chunk_index)
                elif key == "created" and "created_first" in compacted:
                    compacted["created_last"] = value
                elif key == "created" and "created" in compacted and compacted["created"] != value:
                    compacted["created_first"] = compacted.pop("created")
                    compacted["created_last"] = value
                else:
                    set_or_event(compacted, key, value, chunk_index)

            for choice in chunk.get("choices") or []:
                index = choice.get("index", 0)
                compact_choice = choices.setdefault(index, {"index": index, "delta": {}, "events": []})
                delta = choice.get("delta", {})

                for key, value in delta.items():
                    if key in reasoning_keys or key == "content":
                        if value:
                            compact_choice["delta"][key] = compact_choice["delta"].get(key, "") + value
                    elif key == "role":
                        set_or_event(compact_choice["delta"], key, value, chunk_index)
                    else:
                        compact_choice["events"].append({"chunk": chunk_index, "delta": {key: value}})

                for key, value in choice.items():
                    if key in {"index", "delta"}:
                        continue
                    if key == "token_ids" and value:
                        compact_choice.setdefault(key, []).extend(value)
                    elif key == "logprobs" and value is not None:
                        compact_choice.setdefault(key, []).append(value)
                    else:
                        set_or_event(compact_choice, key, value, chunk_index)

        compacted["choices"] = [choices[index] for index in sorted(choices)]

        return compacted
