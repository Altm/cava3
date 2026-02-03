import qrcode

def generate_qr(data: str, filename: str = "qrcode.png", fill_color: str = "black", back_color: str = "white"):
    """
    Генерирует QR-код из переданной строки и сохраняет его в файл.

    :param data: Строка для кодирования (URL, текст и т.д.)
    :param filename: Имя файла для сохранения QR-кода
    :param fill_color: Цвет QR-кода (по умолчанию чёрный)
    :param back_color: Цвет фона (по умолчанию белый)
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=20,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color=fill_color, back_color=back_color)
    img.save(filename)
    print(f"QR-код успешно сохранён как {filename}")

if __name__ == "__main__":
    # Пример использования
    text = input("Введите текст или URL для QR-кода: ").strip()
    if not text:
        text = "https://maps.app.goo.gl/FVq7xJFcpgdzVVj87?g_st=ic"
    output_file = "my_qrcode.png"
    generate_qr(text, output_file)
