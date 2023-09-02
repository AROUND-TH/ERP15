COLUMNS_PRODUCTION_COST_ITEM = [
    {'name': 'ต้นทุนวัตถุดิบที่ใช้ไป', 'children': '', 'type': ''},
    {'name': '', 'children': 'วัตถุดิบเหลือต้นงวด', 'type': 'A'},
    {'name': 'บวก', 'children': 'ซื้อวัตถุดิบ', 'type': 'B'},
    {'name': '', 'children': 'รวมวัตถุดิบที่มีไว้ใช้ผลิต', 'type': 'D'},
    {'name': '', 'children': 'หัก วัตถุดิบคงเหลือยกไป', 'type': 'E'},
    {'name': 'รวมต้นทุนการผลิตใช้ไป', 'children': '', 'type': 'F'},
    {'name': 'ค่าแรงงานทางตรง', 'children': '', 'type': 'G'},
    {'name': 'ค่าใช้จ่ายในการผลิต', 'children': '', 'type': 'H'},
    {'name': 'รวมค่าใช้จ่ายการผลิต', 'children': '', 'type': 'I'},
    {'name': 'ต้นทุนสินค้าที่ผลิตเสร็จ', 'children': '', 'type': 'J'},
    {'name': '', 'children': 'บวก งานระหว่างทำต้นงวด', 'type': 'K'},
    {'name': 'รวมต้นทุนงานที่ผลิตเสร็จ', 'children': '', 'type': 'L'},
    {'name': '', 'children': 'หัก งานระหว่างทำปลายงวด', 'type': 'M'},
    {'name': 'ต้นทุนสินค้าที่ผลิตเสร็จ', 'children': '', 'type': 'N'},
]

COLUMNS_SALES_ITEM = [
    {'name': 'ต้นทุนขาย', 'children': '', 'type': ''},
    {'name': '', 'children': 'สินค้าคงเหลือต้นงวด', 'type': 'A'},
    {'name': '', 'children': 'บวก ต้นทุนสินค้าที่ผลิตเสร็จ', 'type': 'B'},
    {'name': '', 'children': 'ซื้อสินค้าสำเร็จรูป', 'type': 'D'},
    {'name': '', 'children': 'ซื้อสินค้าที่มีไว้เพื่อขาย', 'type': 'E'},
    {'name': '', 'children': 'หัก สินค้าคงเหลือปลายงวด', 'type': 'F'},
    {'name': 'รวมต้นทุนขาย', 'children': '', 'type': 'G'},
]
