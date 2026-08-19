def install(con):
    titles = (
        "Înlocuire baterie - 19 CAN Gateway Long Adaptation Channel 004",
        "Înlocuire baterie - Gateway UDS / Battery adaptation",
        "Înlocuire baterie - 19 CAN Gateway UDS",
    )
    for title in titles:
        con.execute("UPDATE procedure_library SET category='Baterie' WHERE title=?", (title,))

    # Catch existing/future battery replacement records without touching unrelated battery diagnostics.
    con.execute("""
        UPDATE procedure_library
        SET category='Baterie'
        WHERE lower(title) LIKE '%înlocuire baterie%'
           OR lower(title) LIKE '%battery replacement%'
    """)
    con.commit()
