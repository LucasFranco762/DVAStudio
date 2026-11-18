if __name__ == "__main__":
    import sys

    if len(sys.argv) == 3 and sys.argv[1] == "--verificar-distribuicao":
        from pathlib import Path
        from src.dvaStudio.core.distribution_check import verify_distribution

        raise SystemExit(verify_distribution(Path(sys.argv[2])))
    else:
        from src.dvaStudio.app import main

        main()
