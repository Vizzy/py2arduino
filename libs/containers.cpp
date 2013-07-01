#include <stdlib.h>
#include <iostream>

using namespace std;

template <class T>
class List;

template <class T>
class Container
{
public:
	bool _contains(T element)
	{
		for (int i = 0; i < length; ++i)
		{
			if (elts[i] == element)
				return true;
		}
		return false;
	}
	
protected:
	T *elts;
	int length;
};

template <class T>
class Tuple : public Container<T>
{
public:
	Tuple(T *elements, int n)
	{
			this->elts = (T *) malloc(sizeof(T) * n);

			for (int i = 0; i < n; ++i)
			{
				this->elts[i] = elements[i];
			}

			this->length = n;
	}

	int count()
	{
		return this->length;
	}

	int index(T elt)
	{
		for (int i = 0; i < this->length; ++i)
		{
			if (this->elts[i] == elt)
				return i;
		}

		return -1;
	}

	int operator[] (const int n)
	{
	    return this->elts[n];
	}
};

template <class T>
class Node
{
	friend class List<T>;
public:
	Node() : next(NULL){}

	T data;
	Node *next;
};

template <class T>
class List
{
public:
	List()
	{
		length = 0;
	}

	bool contains(T elem)
	{
		Node<T> *cur_elem = &root_elem;
		while(cur_elem != NULL)
		{
			if (cur_elem->data == elem)
			{
				return true;
			}
			cur_elem = cur_elem->next;
		}
		return false;
	}

	void append(T elem)
	{
		Node<T> new_elem;
		new_elem.data = elem;

		if (length == 0)
		{
			root_elem = new_elem;
		}
		else
		{
			Node<T> *cur_elem = get_current_elem();
			cur_elem->next = new Node<T>(new_elem);
		}

		length++;
	}

	int length;
	Node<T> root_elem;

private:
	Node<T> *get_current_elem()
	{
		Node<T> *cur_elem = &root_elem;
		while(cur_elem->next != NULL)
		{
			cur_elem = cur_elem->next;
		}
		return cur_elem;
	}
};

int main(int argc, char const *argv[])
{
	List<int> myList;
	myList.append(1);
	myList.append(5);
	cout << noboolalpha << myList.contains(5) << "\n";
	cout << noboolalpha << myList.contains(3) << "\n";

	return 0;
}