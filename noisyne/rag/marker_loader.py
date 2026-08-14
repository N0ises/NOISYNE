from marker.config.parser import ConfigParser
from marker.models import create_model_dict
from marker.converters.pdf import PdfConverter


def load_pdf(pdf_path):

    config = ConfigParser(
        {
            "output_format": "markdown",
        }
    )

    converter = PdfConverter(
        config=config.generate_config_dict(),
        artifact_dict=create_model_dict(),
        processor_list=config.get_processors(),
        renderer=config.get_renderer(),
    )

    rendered = converter(pdf_path)

    print("=" * 80)
    print("RAW MARKDOWN")
    print("=" * 80)
    print(rendered.markdown[:3000])
    print("=" * 80)

    return [
        {
            "text": rendered.markdown,
            "page": 1,
            "source": pdf_path,
        }
    ]