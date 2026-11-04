from chonkie import Pipeline


if __name__ == "__main__":
    docs = (Pipeline()
            .fetch_from("file", dir="./data/raw/vllm-0.10.1",
                        ext=[".md", ".txt"])
            .process_with("text")
            .chunk_with("recursive", chunk_size=2000)
            .run())

    # Process each document
    for doc in docs:
        print(f"Document has {len(doc.chunks)} chunks")
