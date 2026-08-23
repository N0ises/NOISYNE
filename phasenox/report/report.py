def create_report(engineer, diagnosis, recommendations):

    report = []

    report.append("=" * 40)
    report.append("      SOUND BRAIN REPORT")
    report.append("=" * 40)
    report.append("")

    report.append("Engineer Report")
    report.append("--------------------")
    report.append(engineer)
    report.append("")

    report.append("Diagnosis")
    report.append("--------------------")

    for item in diagnosis:
        report.append(f"• {item}")

    report.append("")
    report.append("Recommendations")
    report.append("--------------------")

    for item in recommendations:
        report.append(f"✓ {item}")

    report.append("")
    report.append("=" * 40)

    return "\n".join(report)


# Backward compatibility
build_report = create_report