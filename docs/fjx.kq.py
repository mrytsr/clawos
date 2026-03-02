#!/usr/bin/env python3
"""分析考勤数据，对比排班和实际打卡"""

import pandas as pd
from collections import defaultdict
import re
from datetime import datetime

def parse_schedule(df):
    """解析 Sheet1 排班表"""
    df = df.iloc[2:].reset_index(drop=True)
    
    schedule = {}
    for _, row in df.iterrows():
        name = row.iloc[0]
        if pd.isna(name) or name == '序号':
            continue
        
        schedule[name] = {}
        for day in range(1, 31):
            col_idx = day + 1
            if col_idx < len(row):
                status = str(row.iloc[col_idx]).strip()
                if status == '√':
                    schedule[name][day] = '出勤'
                elif status == '休':
                    schedule[name][day] = '休假'
                elif status == '-':
                    schedule[name][day] = '休息'
                elif '病' in status or '事' in status or '年' in status:
                    schedule[name][day] = status
                else:
                    schedule[name][day] = status if status and status != 'nan' else '休息'
    
    return schedule

def parse_attendance(df):
    """解析 Sheet2 考勤明细"""
    df = df.dropna(subset=['姓名']).reset_index(drop=True)
    
    attendance = {}
    for _, row in df.iterrows():
        name = row['姓名']
        if pd.isna(name):
            continue
        
        if name not in attendance:
            attendance[name] = {
                'org': row.get('组织名称', ''),
                'work_id': row.get('工号', ''),
                'group': row.get('考勤组', ''),
                'days': {},
                'attendance_days': 0
            }
        
        for day in range(1, 31):
            col_name = str(day)
            for col in df.columns:
                if col.startswith(f'{day}') or col == str(day):
                    time_str = row.get(col, '')
                    if pd.notna(time_str) and time_str not in ['-', '']:
                        times = [t.strip() for t in str(time_str).split('\n') if t.strip()]
                        if times:
                            attendance[name]['days'][day] = times
                            break
        
        if '达标考勤天数' in df.columns:
            try:
                attendance[name]['attendance_days'] = float(df[df['姓名'] == name]['达标考勤天数'].values[0])
            except:
                pass
    
    return attendance

def analyze_attendance(schedule, attendance):
    """分析出勤情况，返回结果数据"""
    results = []
    
    all_names = set(schedule.keys()) | set(attendance.keys())
    
    for name in sorted(all_names):
        # 过滤掉"已删除"的人和记录
        if '(已删除)' in name:
            continue
        
        sched = schedule.get(name, {})
        attend = attendance.get(name, {})
        
        # 过滤掉已删除的组织
        if '(已删除)' in str(attend.get('org', '')):
            continue
        
        org = attend.get('org', '-')
        group = attend.get('group', '-')
        work_id = attend.get('work_id', '-')
        
        scheduled_work = 0
        actual_work = 0
        late_count = 0
        no_sign = 0
        rest_work = 0  # 休息日打卡
        
        day_details = []
        
        for day in range(1, 31):
            s = sched.get(day, '休息')
            times = attend.get('days', {}).get(day, [])
            
            if '休' in s or '假' in s or s == '休息':
                if times:
                    rest_work += 1
                    day_details.append({
                        'day': day,
                        'status': '休息日打卡',
                        'time': ' / '.join(times[:2])
                    })
                continue
            
            if s == '出勤':
                scheduled_work += 1
                if times:
                    first_time = times[0]
                    actual_work += 1
                    
                    try:
                        hour = int(first_time.split(':')[0])
                        minute = int(first_time.split(':')[1]) if ':' in first_time else 0
                        if hour > 9 or (hour == 9 and minute > 30):
                            late_count += 1
                            day_details.append({
                                'day': day,
                                'status': '出勤-迟到',
                                'time': first_time
                            })
                        else:
                            day_details.append({
                                'day': day,
                                'status': '出勤-正常',
                                'time': first_time
                            })
                    except:
                        day_details.append({
                            'day': day,
                            'status': '出勤',
                            'time': first_time
                        })
                else:
                    no_sign += 1
                    day_details.append({
                        'day': day,
                        'status': '缺勤',
                        'time': ''
                    })
        
        results.append({
            '姓名': name,
            '组织': org,
            '考勤组': group,
            '工号': work_id,
            '计划出勤天数': scheduled_work,
            '实际打卡天数': actual_work,
            '缺勤天数': no_sign,
            '休息日打卡天数': rest_work,
            '迟到次数': late_count,
            '达标考勤天数': attend.get('attendance_days', 0),
            '异常记录': '\n'.join([f"{d['day']}日: {d['status']} {d['time']}" for d in day_details[:20]])
        })
    
    return results

def write_excel(results, output_path):
    """写入 Excel 文件"""
    
    # 主表：汇总
    df_summary = pd.DataFrame(results)
    
    # 按组织分组汇总
    org_stats = df_summary.groupby('组织').agg({
        '姓名': 'count',
        '计划出勤天数': 'sum',
        '实际打卡天数': 'sum',
        '缺勤天数': 'sum',
        '迟到次数': 'sum',
        '达标考勤天数': 'sum'
    }).reset_index()
    org_stats.columns = ['组织', '人数', '计划出勤天数', '实际打卡天数', '缺勤天数', '迟到次数', '达标考勤天数']
    org_stats['出勤率'] = (org_stats['实际打卡天数'] / org_stats['计划出勤天数'] * 100).round(1).astype(str) + '%'
    
    # 迟到排行榜
    df_late = df_summary[df_summary['迟到次数'] > 0].sort_values('迟到次数', ascending=False).head(20)
    
    # 缺勤名单
    df_absent = df_summary[df_summary['缺勤天数'] > 0].sort_values('缺勤天数', ascending=False)
    
    # 写入 Excel
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df_summary.to_excel(writer, sheet_name='个人出勤汇总', index=False)
        org_stats.to_excel(writer, sheet_name='组织统计', index=False)
        df_late.to_excel(writer, sheet_name='迟到排行榜', index=False)
        df_absent.to_excel(writer, sheet_name='缺勤名单', index=False)
    
    return org_stats, df_late, df_absent

def main():
    file_path = '/root/.openclaw/workspace/fjx/kq.xlsx'
    output_path = '/root/.openclaw/workspace/fjx/kq-out.xlsx'
    
    print(f"📊 读取文件: {file_path}\n")
    
    xl = pd.ExcelFile(file_path)
    print(f"📋 Sheet: {xl.sheet_names}\n")
    
    print("📑 解析排班表...")
    sched_df = pd.read_excel(xl, sheet_name='Sheet1')
    schedule = parse_schedule(sched_df)
    
    print("📑 解析考勤明细...")
    att_df = pd.read_excel(xl, sheet_name='Sheet2')
    attendance = parse_attendance(att_df)
    
    print("📈 分析中...")
    results = analyze_attendance(schedule, attendance)
    
    print(f"📝 写入 Excel: {output_path}")
    org_stats, df_late, df_absent = write_excel(results, output_path)
    
    print("\n" + "="*60)
    print("✅ 分析完成！")
    print("="*60)
    print(f"\n📁 输出文件: {output_path}")
    print(f"\n📊 Sheets:")
    print("  1. 个人出勤汇总 - 每个人的详细出勤记录")
    print("  2. 组织统计 - 按部门汇总")
    print("  3. 迟到排行榜 - 迟到次数排名")
    print("  4. 缺勤名单 - 有缺勤记录的人")
    
    print(f"\n📈 组织统计:")
    print(org_stats.to_string(index=False))

if __name__ == '__main__':
    main()
