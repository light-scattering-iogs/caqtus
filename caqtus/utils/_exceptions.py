def with_note[E: BaseException](
    exc: E, note: str
) -> E:
    """Add a note to an exception."""
    exc.add_note(note)
    return exc