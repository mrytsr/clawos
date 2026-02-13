def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:
            break
    return arr


def main():
    # 测试用例
    test_arr = [64, 34, 25, 12, 22, 11, 90]
    print("原始数组:", test_arr)
    sorted_arr = bubble_sort(test_arr.copy())
    print("排序后数组:", sorted_arr)
    
    # 额外测试
    test_arr2 = [5, 1, 4, 2, 8]
    print("\n原始数组:", test_arr2)
    sorted_arr2 = bubble_sort(test_arr2.copy())
    print("排序后数组:", sorted_arr2)
    
    # 空数组测试
    test_arr3 = []
    print("\n原始数组:", test_arr3)
    sorted_arr3 = bubble_sort(test_arr3.copy())
    print("排序后数组:", sorted_arr3)
    
    # 已排序数组测试
    test_arr4 = [1, 2, 3, 4, 5]
    print("\n原始数组:", test_arr4)
    sorted_arr4 = bubble_sort(test_arr4.copy())
    print("排序后数组:", sorted_arr4)


if __name__ == "__main__":
    main()