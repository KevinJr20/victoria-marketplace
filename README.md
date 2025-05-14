# 🛒 Victoria Marketplace

Welcome to **Victoria Marketplace** 🌟, an e-commerce platform designed to empower small and medium enterprises (SMEs) and fishers in Kisumu, Kenya. This platform connects local sellers with buyers, offering a seamless online shopping experience with features tailored for the community. Built with Django, it’s robust, scalable, and ready to grow! 🚀

## 📜 Overview

Victoria Marketplace is a web-based application that facilitates buying and selling of goods, focusing on the unique needs of Kisumu's local businesses and fishers. Whether you're a seller listing products or a buyer shopping for local goods, this platform makes it easy and efficient. 🌍

### ✨ Key Features

- **User Authentication** 🔐: Register, login, and manage your profile securely.

- **Product Listings** 📦: Browse products with search, filters, and categories.

- **Cart & Orders** 🛍️: Add items to your cart, checkout, and view order history.

- **Seller Dashboard** 🖥️: Sellers can add, edit, and delete their products.

- **M-Pesa Integration** 💳: Seamless payments via Safaricom M-Pesa (pending credentials setup).

- **Profile Management** 👤: Update your username, email, phone number, and seller status.

- **Product Images** 🖼️: Upload and display product images for better visibility.

## 🛠️ Technologies Used

- **Payments**: M-Pesa via `python-daraja` 💸
- **Version Control**: Git & GitHub 🌐


### 🛠️ Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/KevinJr20/victoria-marketplace.git
   cd victoria-marketplace
    ```

2. **Set Up a Virtual Environment**:
    ```bash
    python -m venv .venv
    source .venv/Scripts/activate  # On Windows
    source .venv/bin/activate  # On macOS/Linux
    ```


3. **Install Python Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

**Note**: If `requirements.txt` isn’t present, install Django and other dependencies manually:

    ```bash
    pip install django django-tailwind python-daraja Pillow
    ```


4. **Apply Database Migrations**:
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```


5. **Create a Superuser**:
    ```bash
    python manage.py createsuperuser
    ```

    Follow the prompts to create an admin user.




## 📖 Usage

**For Buyers** 🛒:

Register or log in at `/register/` or `/login/`.
Browse products on the homepage, use search and filters to find items.
Add items to your cart and proceed to checkout with M-Pesa.
View your order history at `/orders/`.


**For Sellers** 🖥️:

Register as a seller (set `is_seller=True` during registration or via profile update).
Access the Seller Dashboard at `/seller/dashboard/`.
Add, edit, or delete your products.


**For Admins** 🔧:

Log in as a superuser (e.g., `/admin/`).
Manage users, products, categories, and orders.


## 🔮 Future Improvements

**Real-Time Notifications** 🔔: Add WebSocket-based notifications for order updates.

**Live Chat Support** 💬: Implement a chat system for buyer-seller communication.

**Product Reviews** ⭐: Allow users to leave reviews and ratings for products.

**Multiple Payment Options** 💰: Add support for card payments or PayPal.

**Analytics Dashboard** 📊: Provide insights for sellers on sales and product views.


## 🤝 Contributing

We welcome contributions to make Victoria Marketplace even better! 🌟

1. Fork the repository 🍴.

2. Create a new branch:

```bash
    git checkout -b feature/your-feature-name
```


3. Make your changes and commit:

```bash
    git commit -m "Add your feature description"
```


4. Push to your fork:

```bash
    git push origin feature/your-feature-name
```

5. Open a Pull Request on GitHub 📬.

## 📧 Contact

For questions, suggestions, or collaboration, reach out to:

Kevin Omondi Jr. 📩

Email: kevojr69@gmail.com

GitHub: https://github.com/KevinJr20

X: https://x.com/K3V0JR1?s=09


🌟 **Thank you for exploring Victoria Marketplace! Let’s empower Kisumu’s local businesses together!** 🌟
