import transform
from nxd import data_product

if __name__ == "__main__":
    data_product.set_transform(transform.transform)
    data_product.main()
