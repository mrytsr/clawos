"""
仓库管理系统 - Flask Blueprint
"""
import os
from flask import Blueprint, render_template, request, jsonify, send_file
from sqlmodel import Session, select, create_engine, SQLModel
from datetime import datetime
import pandas as pd

# 创建数据库引擎
from config import WAREHOUSE_DB_URL
engine = create_engine(WAREHOUSE_DB_URL, echo=False, pool_pre_ping=True)

from models.warehouse_model import Warehouse, Product, Transaction

warehouse_bp = Blueprint("warehouse", __name__, url_prefix="/warehouse")


from flask import send_from_directory


def _dt(v):
    return v.isoformat() if v else None

@warehouse_bp.route("/")
def index():
    """仓库列表页面"""
    return send_from_directory("static", "warehouse_list.html")



@warehouse_bp.route("/products/<int:warehouse_id>")
def products(warehouse_id):
    """商品列表页面"""
    return send_from_directory("static", "warehouse_products.html")


@warehouse_bp.route("/transactions/<int:warehouse_id>")
@warehouse_bp.route("/transactions/<int:warehouse_id>/<int:product_id>")
def transactions(warehouse_id, product_id=None):
    """明细列表页面"""
    return send_from_directory("static", "warehouse_transactions.html")



def recalculate_stock(session, product_id):
    """从明细重新计算库存"""
    transactions = session.exec(
        select(Transaction)
        .where(Transaction.product_id == product_id)
        .order_by(Transaction.date, Transaction.id)
    ).all()
    stock = 0.0
    for t in transactions:
        if t.type == "入库":
            stock += t.quantity
        else:
            stock -= t.quantity
    product = session.get(Product, product_id)
    if product:
        product.current_stock = stock
        product.mtime = datetime.utcnow()
    return stock

# ========== 仓库 API ==========

@warehouse_bp.route("/api/warehouses", methods=["GET"])
def get_warehouses():
    """获取仓库列表"""
    with Session(engine) as session:
        warehouses = session.exec(select(Warehouse)).all()
        return jsonify([{
            "id": w.id,
            "name": w.name,
            "ctime": _dt(w.ctime),
            "mtime": _dt(w.mtime)
        } for w in warehouses])


@warehouse_bp.route("/api/warehouses", methods=["POST"])
def create_warehouse():
    """创建仓库"""
    data = request.json
    warehouse = Warehouse(
        name=data["name"]
    )
    with Session(engine) as session:
        session.add(warehouse)
        session.commit()
        return jsonify({"id": warehouse.id, "name": warehouse.name})


@warehouse_bp.route("/api/warehouses/<int:warehouse_id>", methods=["GET"])
def get_warehouse(warehouse_id):
    """获取仓库详情"""
    with Session(engine) as session:
        warehouse = session.get(Warehouse, warehouse_id)
        if not warehouse:
            return jsonify({"error": "仓库不存在"}), 404
        
        # 获取商品列表和汇总
        products = session.exec(select(Product).where(Product.warehouse_id == warehouse_id)).all()
        
        total_value = sum(p.current_stock * p.unit_price for p in products)
        
        return jsonify({
            "id": warehouse.id,
            "name": warehouse.name,
            "product_count": len(products),
            "total_value": total_value,
            "ctime": _dt(warehouse.ctime),
            "mtime": _dt(warehouse.mtime)
        })


@warehouse_bp.route("/api/warehouses/<int:warehouse_id>", methods=["DELETE"])
def delete_warehouse(warehouse_id):
    """删除仓库"""
    with Session(engine) as session:
        warehouse = session.get(Warehouse, warehouse_id)
        if not warehouse:
            return jsonify({"error": "仓库不存在"}), 404
        
        # 删除相关数据
        products = session.exec(select(Product).where(Product.warehouse_id == warehouse_id)).all()
        for p in products:
            session.exec(select(Transaction).where(Transaction.product_id == p.id))
            session.query(Transaction).filter(Transaction.product_id == p.id).delete()
        session.query(Product).filter(Product.warehouse_id == warehouse_id).delete()
        session.delete(warehouse)
        session.commit()
        return jsonify({"success": True})


@warehouse_bp.route("/api/warehouses/<int:warehouse_id>", methods=["PUT"])
def update_warehouse(warehouse_id):
    """更新仓库"""
    data = request.json
    with Session(engine) as session:
        warehouse = session.get(Warehouse, warehouse_id)
        if not warehouse:
            return jsonify({"error": "仓库不存在"}), 404
        if "name" in data:
            warehouse.name = data["name"]
        warehouse.mtime = datetime.utcnow()
        session.add(warehouse)
        session.commit()
        return jsonify({"success": True})


# ========== 商品 API ==========

@warehouse_bp.route("/api/warehouse/<int:warehouse_id>/products", methods=["GET"])
def get_products(warehouse_id):
    """获取仓库商品列表"""
    with Session(engine) as session:
        products = session.exec(select(Product).where(Product.warehouse_id == warehouse_id)).all()
        return jsonify([{
            "id": p.id,
            "name": p.name,
            "unit_price": p.unit_price,
            "unit": p.unit,
            "current_stock": p.current_stock,
            "total_value": p.current_stock * p.unit_price
        } for p in products])


@warehouse_bp.route("/api/warehouse/<int:warehouse_id>/products", methods=["POST"])
def create_product(warehouse_id):
    """添加商品"""
    data = request.json
    product = Product(
        warehouse_id=warehouse_id,
        name=data["name"],
        unit_price=float(data.get("unit_price", 0)),
        unit=data.get("unit", "斤"),
        current_stock=float(data.get("current_stock", 0))
    )
    with Session(engine) as session:
        session.add(product)
        session.commit()
        return jsonify({"id": product.id, "name": product.name})


@warehouse_bp.route("/api/product/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    """更新商品"""
    data = request.json
    with Session(engine) as session:
        product = session.get(Product, product_id)
        if not product:
            return jsonify({"error": "商品不存在"}), 404
        
        if "name" in data:
            product.name = data["name"]
        if "unit_price" in data:
            product.unit_price = float(data["unit_price"])
        if "unit" in data:
            product.unit = data["unit"]
        product.mtime = datetime.utcnow()
        
        session.add(product)
        session.commit()
        return jsonify({"success": True})


@warehouse_bp.route("/api/product/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    """删除商品"""
    with Session(engine) as session:
        product = session.get(Product, product_id)
        if not product:
            return jsonify({"error": "商品不存在"}), 404
        
        # 删除出入库记录
        session.query(Transaction).filter(Transaction.product_id == product_id).delete()
        session.delete(product)
        session.commit()
        return jsonify({"success": True})


# ========== 出入库 API ==========

@warehouse_bp.route("/api/product/<int:product_id>/transactions", methods=["GET"])
def get_transactions(product_id):
    """获取商品出入库记录"""
    limit = request.args.get("limit", 50, type=int)
    with Session(engine) as session:
        transactions = session.exec(
            select(Transaction)
            .where(Transaction.product_id == product_id)
            .order_by(Transaction.date.desc(), Transaction.id.desc())
            .limit(limit)
        ).all()
        return jsonify([{
            "id": t.id,
            "type": t.type,
            "quantity": t.quantity,
            "date": t.date,
            "note": t.note,
            "ctime": _dt(t.ctime),
            "mtime": _dt(t.mtime)
        } for t in transactions])


@warehouse_bp.route("/api/warehouse/<int:warehouse_id>/all-transactions")
def get_all_transactions(warehouse_id):
    """获取仓库所有出入库记录"""
    limit = request.args.get("limit", 100, type=int)
    with Session(engine) as session:
        # 获取仓库所有商品
        products = session.exec(select(Product).where(Product.warehouse_id == warehouse_id)).all()
        product_map = {p.id: p.name for p in products}
        
        # 获取这些商品的所有交易记录
        transactions = session.exec(
            select(Transaction)
            .where(Transaction.product_id.in_(list(product_map.keys())))
            .order_by(Transaction.date.desc(), Transaction.id.desc())
            .limit(limit)
        ).all()
        
        return jsonify([{
            "id": t.id,
            "product_id": t.product_id,
            "product_name": product_map.get(t.product_id, "未知"),
            "type": t.type,
            "quantity": t.quantity,
            "date": t.date,
            "note": t.note,
            "ctime": _dt(t.ctime),
            "mtime": _dt(t.mtime)
        } for t in transactions])


@warehouse_bp.route("/api/product/<int:product_id>/transaction", methods=["POST"])
def add_transaction(product_id):
    """添加出入库记录"""
    data = request.json
    tx_type = data["type"]  # 入库 / 出库
    quantity = float(data["quantity"])
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    note = data.get("note", "")
    
    with Session(engine) as session:
        product = session.get(Product, product_id)
        if not product:
            return jsonify({"error": "商品不存在"}), 404
        
        transaction = Transaction(
            product_id=product_id,
            type=tx_type,
            quantity=quantity,
            date=date,
            note=note
        )
        session.add(transaction)
        session.commit()
        
        # 重新计算库存
        recalculate_stock(session, product_id)
        session.commit()
        
        return jsonify({
            "id": transaction.id
        })


# ========== 报表 API ==========

@warehouse_bp.route("/api/warehouse/<int:warehouse_id>/report")
def generate_report(warehouse_id):
    """生成 Excel 报表"""
    with Session(engine) as session:
        warehouse = session.get(Warehouse, warehouse_id)
        if not warehouse:
            return jsonify({"error": "仓库不存在"}), 404
        
        # 获取所有商品
        products = session.exec(select(Product).where(Product.warehouse_id == warehouse_id)).all()
        
        # 汇总序号
        product_list = list(products)
        
        # 明细数据
        details = []
        for idx, p in enumerate(product_list, 1):
            transactions = session.exec(
                select(Transaction)
                .where(Transaction.product_id == p.id)
                .order_by(Transaction.date, Transaction.id)
            ).all()
            
            if not transactions:
                # 无明细时，导出一行初始库存（变动数量=当前库存）
                details.append({
                    "错误": None,
                    "物品名称": f"{idx}.{p.name}({p.unit_price})",
                    "变动数量": int(p.current_stock),
                    "当前库存": int(p.current_stock),
                    "总价值": int(p.current_stock * p.unit_price),
                    "操作时间": None,
                    "操作类型": "入库",
                    "备注/原因": "期初库存"
                })
            else:
                stock = 0.0
                for t in transactions:
                    qty = t.quantity if t.type == "入库" else -t.quantity
                    stock += qty
                    details.append({
                        "错误": None,
                        "物品名称": f"{idx}.{p.name}({p.unit_price})",
                        "变动数量": int(qty),
                        "当前库存": int(stock),
                        "总价值": int(stock * p.unit_price),
                        "操作时间": t.date,
                        "操作类型": t.type,
                        "备注/原因": t.note or ""
                    })
        
        df_detail = pd.DataFrame(details)
        
        # 导出 Excel
        output_path = f"/tmp/warehouse_{warehouse_id}_{datetime.now().strftime('%Y%m%d-%H%M%S')}.xlsx"
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df_detail.to_excel(writer, index=False, sheet_name="明细表")
        
        return send_file(output_path, as_attachment=True, download_name=f"{warehouse.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")


@warehouse_bp.route("/api/warehouse/<int:warehouse_id>/import", methods=["POST"])
def import_excel(warehouse_id):
    """从 Excel 导入数据"""
    if 'file' not in request.files:
        return jsonify({"error": "请选择文件"}), 400
    
    file = request.files['file']
    if not file.filename.endswith('.xlsx'):
        return jsonify({"error": "只支持 xlsx 格式"}), 400
    
    try:
        df = pd.read_excel(file, sheet_name=None)
    except Exception as e:
        return jsonify({"error": f"读取文件失败: {str(e)}"}), 400
    
    with Session(engine) as session:
        warehouse = session.get(Warehouse, warehouse_id)
        if not warehouse:
            return jsonify({"error": "仓库不存在"}), 404
        
        # 先删除该仓库的所有商品和明细
        products = session.exec(select(Product).where(Product.warehouse_id == warehouse_id)).all()
        for p in products:
            session.query(Transaction).filter(Transaction.product_id == p.id).delete()
        session.query(Product).filter(Product.warehouse_id == warehouse_id).delete()
        session.commit()
        
        # 解析明细表
        if "明细表" in df:
            df_detail = df["明细表"]
            product_data = {}  # name -> {unit_price, id}
            
            # 第一遍：创建所有商品
            for _, row in df_detail.iterrows():
                name_raw = row.get("物品名称", "")
                if pd.isna(name_raw) or not name_raw:
                    continue
                
                # 解析名称和单价: "1.虾仁(125)"
                import re
                match = re.match(r'^\d+\.([^\(]+)\((\d+)\)$', str(name_raw))
                if match:
                    name = match.group(1).strip()
                    unit_price = float(match.group(2))
                else:
                    name = str(name_raw).strip()
                    unit_price = 0
                
                if name not in product_data:
                    product = Product(
                        warehouse_id=warehouse_id,
                        name=name,
                        unit_price=unit_price,
                        unit="斤",
                        current_stock=0
                    )
                    session.add(product)
                    session.flush()
                    product_data[name] = {"unit_price": unit_price, "id": product.id}
            
            session.commit()
            
            # 第二遍：处理出入库记录
            touched_product_ids = set()
            for _, row in df_detail.iterrows():
                name_raw = row.get("物品名称", "")
                if pd.isna(name_raw) or not name_raw:
                    continue
                
                # 解析名称
                import re
                match = re.match(r'^\d+\.([^\(]+)\((\d+)\)$', str(name_raw))
                if match:
                    name = match.group(1).strip()
                else:
                    name = str(name_raw).strip()
                
                if name not in product_data:
                    continue
                
                product_id = product_data[name]["id"]
                
                # 处理出入库记录
                qty = row.get("变动数量")
                date = row.get("操作时间")
                tx_type = row.get("操作类型")
                note = row.get("备注/原因") or row.get("备注") or ""
                
                if pd.notna(qty) and pd.notna(tx_type) and tx_type in ["入库", "出库"]:
                    quantity = abs(float(qty))
                    
                    if pd.notna(date):
                        date = str(date)[:10]
                    else:
                        date = datetime.now().strftime("%Y-%m-%d")
                    
                    product = session.get(Product, product_id)
                    if tx_type == "出库":
                        stock_after = product.current_stock - quantity
                    else:
                        stock_after = product.current_stock + quantity
                    
                    tx = Transaction(
                        product_id=product_id,
                        type=tx_type,
                        quantity=quantity,
                        date=date,
                        note=str(note).strip() if pd.notna(note) else ""
                    )
                    session.add(tx)
                    product.current_stock = stock_after
                    product.mtime = datetime.utcnow()
                    touched_product_ids.add(product_id)
            
            session.commit()
            for pid in touched_product_ids:
                recalculate_stock(session, pid)
            session.commit()
        
    return jsonify({"success": True, "message": "导入成功"})


@warehouse_bp.route("/api/transaction/<int:tx_id>", methods=["PUT"])
def update_transaction(tx_id):
    """更新出入库记录"""
    data = request.json
    with Session(engine) as session:
        tx = session.get(Transaction, tx_id)
        if not tx:
            return jsonify({"error": "记录不存在"}), 404
        
        # 更新记录
        if "type" in data:
            tx.type = data["type"]
        if "quantity" in data:
            tx.quantity = float(data["quantity"])
        if "date" in data:
            tx.date = data["date"]
        if "note" in data:
            tx.note = data["note"]
        tx.mtime = datetime.utcnow()
        
        session.add(tx)
        session.commit()
        
        # 重新计算库存
        recalculate_stock(session, tx.product_id)
        session.commit()
        
        return jsonify({"success": True})


@warehouse_bp.route("/api/transaction/<int:tx_id>", methods=["DELETE"])
def delete_transaction(tx_id):
    """删除出入库记录"""
    with Session(engine) as session:
        tx = session.get(Transaction, tx_id)
        if not tx:
            return jsonify({"error": "记录不存在"}), 404
        
        product_id = tx.product_id
        session.delete(tx)
        session.commit()
        
        # 重新计算库存
        recalculate_stock(session, product_id)
        session.commit()
        
        return jsonify({"success": True})
